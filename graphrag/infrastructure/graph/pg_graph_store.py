"""
PostgresGraphStore — `IGraphStore`'un PostgreSQL uygulaması.

Graf, iki tabloda saklanır: `graph_nodes` (düğümler) ve `graph_edges`
(kenarlar). Dijkstra araması yine Python tarafında (`GraphSearchEngine`)
çalışır; bu depo sadece `neighbors()` ile komşu kenarları döndürür — yani
Neo4j gibi ayrı bir graf veritabanına gerek kalmaz.
"""
from __future__ import annotations

from typing import List

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from graphrag.domain.entities import GraphEdge, GraphNode
from graphrag.domain.interfaces import IGraphStore
from graphrag.infrastructure.db.models import GraphEdgeRow, GraphNodeRow


class PostgresGraphStore(IGraphStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert_node(self, node: GraphNode) -> None:
        with Session(self._engine) as session:
            session.merge(GraphNodeRow(node_id=node.node_id, label=node.label))
            session.commit()

    def upsert_edge(self, edge: GraphEdge) -> None:
        with Session(self._engine) as session:
            session.merge(GraphEdgeRow(
                source_id=edge.source_id,
                target_id=edge.target_id,
                weight=edge.weight,
                confidence=edge.confidence,
                relation=edge.relation,
            ))
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
