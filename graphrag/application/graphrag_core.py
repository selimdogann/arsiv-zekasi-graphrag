"""
GraphRAGCore — uygulama katmanı (kullanım senaryolarını yöneten "orkestra şefi").

Bu sınıf HİÇBİR somut teknolojiyi bilmez — sadece `domain/interfaces.py`'deki
PORT'lara bağımlıdır. Hangi somut loader'ın kullanıldığı, constructor'dan
(Dependency Injection ile) dışarıdan verilir.
"""
from __future__ import annotations

from graphrag.domain.entities import Document, DocumentState
from graphrag.domain.interfaces import IDocumentLoader


class GraphRAGCore:
    def __init__(self, loader: IDocumentLoader) -> None:
        self._loader = loader

    def ingest(self, uri: str) -> Document:
        document = self._loader.load(uri)
        document.transition_to(DocumentState.PARSING, note="ingest başladı")
        document.transition_to(DocumentState.PARSED, note="metin hazır")
        return document
