"""
PostgresGraphStore — `IGraphStore`'un PostgreSQL uygulaması.

Graf, iki tabloda saklanır: `graph_nodes` (düğümler) ve `graph_edges`
(kenarlar). Dijkstra araması yine Python tarafında (`GraphSearchEngine`)
çalışır; bu depo sadece `neighbors()` ile komşu kenarları döndürür — yani
Neo4j gibi ayrı bir graf veritabanına gerek kalmaz.
"""
from __future__ import annotations

from typing import List

from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from graphrag.domain.entities import GraphEdge, GraphNode
from graphrag.domain.interfaces import IGraphStore
from graphrag.infrastructure.db.models import (
    EdgeSourceRow,
    GraphEdgeRow,
    GraphNodeRow,
    NodeSourceRow,
)


class PostgresGraphStore(IGraphStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert_node(self, node: GraphNode, document_id: str = "") -> None:
        with Session(self._engine) as session:
            session.merge(GraphNodeRow(node_id=node.node_id, label=node.label))
            if document_id:
                session.merge(NodeSourceRow(node_id=node.node_id,
                                            document_id=document_id))
            session.commit()

    def upsert_edge(self, edge: GraphEdge, document_id: str = "") -> None:
        with Session(self._engine) as session:
            session.merge(GraphEdgeRow(
                source_id=edge.source_id,
                target_id=edge.target_id,
                weight=edge.weight,
                confidence=edge.confidence,
                relation=edge.relation,
            ))
            if document_id:
                session.merge(EdgeSourceRow(source_id=edge.source_id,
                                            target_id=edge.target_id,
                                            document_id=document_id))
            session.commit()

    def neighbors(self, node_id: str) -> List[GraphEdge]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(GraphEdgeRow).where(GraphEdgeRow.source_id == node_id)
            ).scalars().all()
            return [
                GraphEdge(r.source_id, r.target_id, r.weight, r.confidence, r.relation or "")
                for r in rows
            ]

    def get_node(self, node_id: str) -> GraphNode:
        with Session(self._engine) as session:
            row = session.get(GraphNodeRow, node_id)
            if row is None:
                raise KeyError(node_id)
            return GraphNode(node_id=row.node_id, label=row.label)

    def all_nodes(self) -> List[GraphNode]:
        with Session(self._engine) as session:
            rows = session.execute(select(GraphNodeRow)).scalars().all()
            return [GraphNode(node_id=r.node_id, label=r.label) for r in rows]

    def edge_count(self) -> int:
        with Session(self._engine) as session:
            return session.execute(
                select(func.count()).select_from(GraphEdgeRow)).scalar_one()

    def delete_document(self, document_id: str) -> None:
        """Belgenin graftaki katkısını geri alır (bkz. IGraphStore — köken).

        Yalnızca BU belgenin dokunduğu düğüm/kenarlar incelenir; köken kaydı
        hiç olmayan (bu özellikten önce oluşmuş) satırlara dokunulmaz.
        """
        with Session(self._engine) as session:
            etkilenen_dugum = session.execute(
                select(NodeSourceRow.node_id)
                .where(NodeSourceRow.document_id == document_id)
            ).scalars().all()
            etkilenen_kenar = session.execute(
                select(EdgeSourceRow.source_id, EdgeSourceRow.target_id)
                .where(EdgeSourceRow.document_id == document_id)
            ).all()

            # 1) Belgenin kökenini sil.
            session.execute(delete(NodeSourceRow)
                            .where(NodeSourceRow.document_id == document_id))
            session.execute(delete(EdgeSourceRow)
                            .where(EdgeSourceRow.document_id == document_id))
            session.flush()

            # 2) Başka belge desteklemiyorsa düğüm/kenarın kendisini sil.
            for node_id in etkilenen_dugum:
                kalan = session.execute(
                    select(func.count()).select_from(NodeSourceRow)
                    .where(NodeSourceRow.node_id == node_id)).scalar_one()
                if kalan == 0:
                    session.execute(delete(GraphNodeRow)
                                    .where(GraphNodeRow.node_id == node_id))
                    # Öksüz düğüme bağlı kenar (ve kökeni) kalmasın: aksi hâlde
                    # Dijkstra var olmayan bir düğüme yürümeye çalışır.
                    session.execute(delete(GraphEdgeRow).where(
                        (GraphEdgeRow.source_id == node_id)
                        | (GraphEdgeRow.target_id == node_id)))
                    session.execute(delete(EdgeSourceRow).where(
                        (EdgeSourceRow.source_id == node_id)
                        | (EdgeSourceRow.target_id == node_id)))

            for kaynak, hedef in etkilenen_kenar:
                kalan = session.execute(
                    select(func.count()).select_from(EdgeSourceRow)
                    .where(EdgeSourceRow.source_id == kaynak,
                           EdgeSourceRow.target_id == hedef)).scalar_one()
                if kalan == 0:
                    session.execute(delete(GraphEdgeRow).where(
                        GraphEdgeRow.source_id == kaynak,
                        GraphEdgeRow.target_id == hedef))

            session.commit()
