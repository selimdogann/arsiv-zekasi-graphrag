"""
GraphSearchEngine — Dijkstra tabanlı, en güvenilir yolu bulan arama motoru.

Kenar ağırlıkları -log(confidence) olduğundan (bkz. proje notları), EN KISA
yol = EN GÜVENİLİR ilişki zinciridir. Ağırlıklar her zaman >= 0 olduğundan
Dijkstra, optimal (en iyi) sonucu garanti eder.
"""
from __future__ import annotations

import heapq
from typing import Dict

from graphrag.domain.entities import GraphPath
from graphrag.domain.exceptions import PathNotFoundError
from graphrag.domain.interfaces import IGraphStore


class GraphSearchEngine:
    def __init__(self, graph: IGraphStore) -> None:
        self._graph = graph

    def shortest_path(self, source_id: str, target_id: str) -> GraphPath:
        dist: Dict[str, float] = {source_id: 0.0}
        prev: Dict[str, str] = {}
        heap = [(0.0, source_id)]

        while heap:
            d, u = heapq.heappop(heap)
            if d > dist.get(u, float("inf")):
                continue  # bayat kayıt: zaten daha iyi bir yol bulunmuş
            if u == target_id:
                break

            for edge in self._graph.neighbors(u):
                nd = d + edge.weight
                if nd < dist.get(edge.target_id, float("inf")):
                    dist[edge.target_id] = nd
                    prev[edge.target_id] = u
                    heapq.heappush(heap, (nd, edge.target_id))

        if target_id not in dist:
            raise PathNotFoundError(f"{source_id} -> {target_id}")

        path_nodes = [target_id]
        cursor = target_id
        while cursor != source_id:
            cursor = prev[cursor]
            path_nodes.append(cursor)
        path_nodes.reverse()

        return GraphPath(nodes=tuple(path_nodes), total_cost=dist[target_id])
