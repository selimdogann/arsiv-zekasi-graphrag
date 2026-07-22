"""
InMemoryVectorStore — `IVectorStore`'un bellek-içi uygulaması.

Vektörler eklenirken NORMALİZE edilir (uzunluğu 1 yapılır); böylece arama
anında kosinüs benzerliği = sadece nokta çarpımı olur (daha hızlı hesaplama).
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from graphrag.domain.entities import Chunk
from graphrag.domain.interfaces import IVectorStore


class InMemoryVectorStore(IVectorStore):
    def __init__(self) -> None:
        self._chunks: Dict[str, Chunk] = {}
        self._normalized: Dict[str, Tuple[float, ...]] = {}

    @staticmethod
    def _normalize(vec: Tuple[float, ...]) -> Tuple[float, ...]:
        length = math.sqrt(sum(x * x for x in vec))
        if length == 0.0:
            return vec
        return tuple(x / length for x in vec)

    def upsert(self, chunks: List[Chunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._normalized[chunk.chunk_id] = self._normalize(chunk.embedding)

    def search(self, query_embedding: Tuple[float, ...], top_k: int):
        q = self._normalize(query_embedding)
        scored = []
        for chunk_id, vec in self._normalized.items():
            similarity = sum(a * b for a, b in zip(q, vec))
            scored.append((self._chunks[chunk_id], similarity))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
