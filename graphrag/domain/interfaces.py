"""
Ports (Abstract Base Class'lar) — Clean Architecture'ın "sınır" katmanı.

Bu ABC'ler, sistemin dış dünyadan ne İSTEDİĞİNİ tanımlar; NASIL sağlandığını
değil. Somut altyapı (bir dosya okuyucu, bir PDF ayrıştırıcı, bir LLM istemcisi)
bu sözleşmeleri UYGULAR. Domain, hangi somut teknolojinin kullanıldığını
asla bilmez — bu, düşük bağımlılığın (low coupling) temelidir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List,Tuple


from graphrag.domain.entities import Document, GraphEdge, GraphNode, Chunk


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



class IVectorStore(ABC):
    """Vektör benzerliği araması sözleşmesi."""

    @abstractmethod
    def upsert(self, chunks: List[Chunk]) -> None:
        """Chunk'ları depoya ekler/günceller."""

    @abstractmethod
    def search(self, query_embedding: Tuple[float, ...], top_k: int
               ) -> List["tuple[Chunk, float]"]:
        """En benzer top_k chunk'ı, (chunk, benzerlik_skoru) çiftleri olarak döndürür."""


class ILanguageModel(ABC):
    """LLM (dil modeli) çıkarım sözleşmesi."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Verilen prompt'un devamını (LLM'in ürettiği metni) döndürür."""
