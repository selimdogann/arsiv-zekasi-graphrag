"""
InMemoryDocumentCatalog — `IDocumentCatalog`'un bellek-içi uygulaması.

Uygulama kapanınca kayıt da kaybolur; kalıcılık için `PostgresDocumentCatalog`
kullanılır (bkz. composition.py).
"""
from __future__ import annotations

from typing import Dict, List

from graphrag.domain.entities import DocumentInfo
from graphrag.domain.interfaces import IDocumentCatalog


class InMemoryDocumentCatalog(IDocumentCatalog):
    def __init__(self) -> None:
        self._kayitlar: Dict[str, DocumentInfo] = {}

    def add(self, info: DocumentInfo) -> None:
        self._kayitlar[info.document_id] = info      # aynı id -> güncelle

    def all(self) -> List[DocumentInfo]:
        return sorted(self._kayitlar.values(),
                      key=lambda k: k.created_at, reverse=True)

    def remove(self, document_id: str) -> None:
        self._kayitlar.pop(document_id, None)
