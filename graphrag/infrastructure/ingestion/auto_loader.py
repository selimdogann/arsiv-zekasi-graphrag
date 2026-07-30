"""
AutoDocumentLoader — dosya uzantısına bakıp doğru somut `IDocumentLoader`'a
işi devreden bir yönlendirici (Strategy deseni).

Kendisi de `IDocumentLoader` sözleşmesini uyguladığı için `GraphRAGCore`'un
gözünde tek bir loader'dan farksızdır — hangi uzantının hangi sınıfa gittiği
kararı SADECE burada verilir.
"""
from __future__ import annotations

import os

from graphrag.domain.entities import Document
from graphrag.domain.exceptions import IngestionError
from graphrag.domain.interfaces import IDocumentLoader
from graphrag.infrastructure.ingestion.document_loader import PlainTextLoader
from graphrag.infrastructure.ingestion.docx_loader import DocxLoader
from graphrag.infrastructure.ingestion.pdf_loader import PdfLoader


class AutoDocumentLoader(IDocumentLoader):
    def __init__(self) -> None:
        self._loaders_by_extension = {
            ".txt": PlainTextLoader(),
            ".pdf": PdfLoader(),
            ".docx": DocxLoader(),
        }

    def load(self, uri: str) -> Document:
        extension = os.path.splitext(uri)[1].lower()
        loader = self._loaders_by_extension.get(extension)
        if loader is None:
            raise IngestionError(f"Desteklenmeyen dosya türü: {extension or '(uzantısız)'}")
        return loader.load(uri)
