"""
PlainTextLoader — `IDocumentLoader` sözleşmesinin ilk somut (concrete) uygulaması.

Bir .txt dosyasını okuyup bir `Document` nesnesine çevirir. Dosya bulunamazsa
veya okunamazsa, Python'ın kendi hatasını YAKALAYIP domain'in `IngestionError`
istisnasına çevirir (exception translation) — böylece dışarıdaki hiçbir kod,
burada `open()` kullanıldığını bilmek zorunda kalmaz.
"""
from __future__ import annotations

import os

from graphrag.domain.entities import Document
from graphrag.domain.exceptions import IngestionError
from graphrag.domain.interfaces import IDocumentLoader


class PlainTextLoader(IDocumentLoader):
    def load(self, uri: str) -> Document:
        if not os.path.isfile(uri):
            raise IngestionError(f"Dosya bulunamadı: {uri}")
        try:
            with open(uri, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            raise IngestionError(f"Dosya okunamadı: {uri}") from exc

        title = os.path.splitext(os.path.basename(uri))[0]
        return Document(uri=uri, title=title, raw_text=text)
