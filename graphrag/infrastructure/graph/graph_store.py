"""
InMemoryGraphStore — `IGraphStore`'un bellek-içi (in-memory) uygulaması.

"Komşuluk listesi" (adjacency list) deseni kullanılır: her düğüm için,
ondan ÇIKAN kenarlar tutulur. Bu, `neighbors(node_id)` çağrısını hızlı
(O(çıkış derecesi)) yapar — Dijkstra'nın ihtiyaç duyduğu tam olarak budur.

Kenarlar `(kaynak, hedef)` çiftiyle anahtarlanır: aynı kenar tekrar
eklendiğinde çoğalmaz, GÜNCELLENİR (Postgres uygulamasıyla aynı davranış).

Ayrıca her düğüm ve kenar için KÖKEN tutulur: "beni hangi belgeler
destekliyor". Belge silinince kökenden düşülür; desteksiz kalan düğüm ve
kenarlar grafı terk eder.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from graphrag.domain.entities import GraphEdge, GraphNode
from graphrag.domain.interfaces import IGraphStore

_KenarAnahtari = Tuple[str, str]


class InMemoryGraphStore(IGraphStore):
    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        # kaynak -> {hedef: kenar}
        self._out: Dict[str, Dict[str, GraphEdge]] = defaultdict(dict)
        # köken: düğüm/kenar -> onu üreten belge id'leri
        self._node_docs: Dict[str, Set[str]] = defaultdict(set)
        self._edge_docs: Dict[_KenarAnahtari, Set[str]] = defaultdict(set)

    def upsert_node(self, node: GraphNode, document_id: str = "") -> None:
        self._nodes[node.node_id] = node
        if document_id:
            self._node_docs[node.node_id].add(document_id)

    def upsert_edge(self, edge: GraphEdge, document_id: str = "") -> None:
        self._out[edge.source_id][edge.target_id] = edge
        if document_id:
            self._edge_docs[(edge.source_id, edge.target_id)].add(document_id)

    def neighbors(self, node_id: str) -> List[GraphEdge]:
        return list(self._out.get(node_id, {}).values())

    def get_node(self, node_id: str) -> GraphNode:
        return self._nodes[node_id]

    def all_nodes(self) -> List[GraphNode]:
        return list(self._nodes.values())

    def edge_count(self) -> int:
        return sum(len(hedefler) for hedefler in self._out.values())

    def delete_document(self, document_id: str) -> None:
        # Kenarlar: kökenden belgeyi düş, desteksiz kalanı sil.
        for (kaynak, hedef), belgeler in list(self._edge_docs.items()):
            belgeler.discard(document_id)
            if belgeler:
                continue
            del self._edge_docs[(kaynak, hedef)]
            self._out.get(kaynak, {}).pop(hedef, None)

        # Düğümler: aynı mantık.
        for node_id, belgeler in list(self._node_docs.items()):
            belgeler.discard(document_id)
            if belgeler:
                continue
            del self._node_docs[node_id]
            self._nodes.pop(node_id, None)
            # Artık var olmayan düğümden çıkan/ona giren kenar kalmasın:
            # öksüz kenar bırakılırsa Dijkstra yok olan bir düğüme yürümeye
            # çalışır ve `get_node` KeyError verir.
            for hedef in self._out.pop(node_id, {}):
                self._edge_docs.pop((node_id, hedef), None)
            for kaynak, hedefler in self._out.items():
                if hedefler.pop(node_id, None) is not None:
                    self._edge_docs.pop((kaynak, node_id), None)
