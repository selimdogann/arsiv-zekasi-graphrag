"""
PdfLoader — `IDocumentLoader` sözleşmesinin PDF uygulaması.

Bir .pdf dosyasını sayfa sayfa okuyup metnini birleştirir, bir `Document`
nesnesine çevirir. `PlainTextLoader` ile birebir aynı iskelet — sadece
dosya okuma kısmı farklı.
"""
from __future__ import annotations

import os

from pypdf import PdfReader

from graphrag.domain.entities import Document
from graphrag.domain.exceptions import IngestionError
from graphrag.domain.interfaces import IDocumentLoader


class PdfLoader(IDocumentLoader):
    def load(self, uri: str) -> Document:
        if not os.path.isfile(uri):
            raise IngestionError(f"Dosya bulunamadı: {uri}")
        try:
            reader = PdfReader(uri)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as exc:
            raise IngestionError(f"PDF okunamadı: {uri}") from exc

        title = os.path.splitext(os.path.basename(uri))[0]
        return Document(uri=uri, title=title, raw_text=text)
