"""
InMemoryGraphStore — `IGraphStore`'un bellek-içi (in-memory) uygulaması.

"Komşuluk listesi" (adjacency list) deseni kullanılır: her düğüm için,
ondan ÇIKAN kenarların bir listesi tutulur. Bu, `neighbors(node_id)`
çağrısını hızlı (O(çıkış derecesi)) yapar — Dijkstra'nın ihtiyaç duyduğu
tam olarak budur.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from graphrag.domain.entities import GraphEdge, GraphNode
from graphrag.domain.interfaces import IGraphStore


class InMemoryGraphStore(IGraphStore):
    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)

    def upsert_node(self, node: GraphNode) -> None:
        self._nodes[node.node_id] = node

    def upsert_edge(self, edge: GraphEdge) -> None:
        self._adjacency[edge.source_id].append(edge)

    def neighbors(self, node_id: str) -> List[GraphEdge]:
        return list(self._adjacency.get(node_id, []))
