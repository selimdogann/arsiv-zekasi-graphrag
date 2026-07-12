"""
Ports (Abstract Base Class'lar) — Clean Architecture'ın "sınır" katmanı.

Bu ABC'ler, sistemin dış dünyadan ne İSTEDİĞİNİ tanımlar; NASIL sağlandığını
değil. Somut altyapı (bir dosya okuyucu, bir PDF ayrıştırıcı, bir LLM istemcisi)
bu sözleşmeleri UYGULAR. Domain, hangi somut teknolojinin kullanıldığını
asla bilmez — bu, düşük bağımlılığın (low coupling) temelidir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from graphrag.domain.entities import Document


class IDocumentLoader(ABC):
    """Ham bir kaynağı (dosya, URL, ...) bir `Document`'a çeviren sözleşme."""

    @abstractmethod
    def load(self, uri: str) -> Document:
        """Verilen kaynaktan bir Document oluşturur."""
