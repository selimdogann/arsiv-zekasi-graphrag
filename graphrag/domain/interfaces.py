"""
Ports (Abstract Base Class'lar) — Clean Architecture'ın "sınır" katmanı.

Bu ABC'ler, sistemin dış dünyadan ne İSTEDİĞİNİ tanımlar; NASIL sağlandığını
değil. Somut altyapı (bir dosya okuyucu, bir PDF ayrıştırıcı, bir LLM istemcisi)
bu sözleşmeleri UYGULAR. Domain, hangi somut teknolojinin kullanıldığını
asla bilmez — bu, düşük bağımlılığın (low coupling) temelidir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


from graphrag.domain.entities import Document, GraphEdge, GraphNode


class IDocumentLoader(ABC):
    """Ham bir kaynağı (dosya, URL, ...) bir `Document`'a çeviren sözleşme."""

    @abstractmethod
    def load(self, uri: str) -> Document:
        """Verilen kaynaktan bir Document oluşturur."""


class IGraphStore(ABC):
    """Bilgi çizgesi depolama sözleşmesi."""

    @abstractmethod
    def upsert_node(self, node: GraphNode) -> None:
        """Düğümü ekler/günceller."""

    @abstractmethod
    def upsert_edge(self, edge: GraphEdge) -> None:
        """Kenarı ekler/günceller."""

    @abstractmethod
    def neighbors(self, node_id: str) -> List[GraphEdge]:
        """Verilen düğümden ÇIKAN tüm kenarları döndürür (komşuluk listesi)."""
