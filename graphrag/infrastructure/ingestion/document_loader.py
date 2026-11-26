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


# Denenecek kodlamalar, sırayla. Türkiye'de Windows'ta (Not Defteri'nin eski
# sürümleri, eski kurum sistemleri) kaydedilmiş .txt dosyaları çoğunlukla
# UTF-8 değil cp1254'tür; yalnızca UTF-8 denendiğinde bu belgeler 500 hatasıyla
# düşüyordu. "utf-8-sig", baştaki BOM işaretini de temizler.
_KODLAMALAR = ("utf-8-sig", "cp1254")


class PlainTextLoader(IDocumentLoader):
    def load(self, uri: str) -> Document:
        if not os.path.isfile(uri):
            raise IngestionError(f"Dosya bulunamadı: {os.path.basename(uri)}")
        try:
            with open(uri, "rb") as fh:
                ham = fh.read()
        except OSError as exc:
            raise IngestionError(f"Dosya okunamadı: {os.path.basename(uri)}") from exc

        # NUL baytı düz metinde olmaz; ikili dosya ya da UTF-16'dır. cp1254
        # neredeyse her baytı çözdüğü için bu kontrol olmadan çöp metin girerdi.
        if b"\x00" in ham:
            raise IngestionError(
                "Dosya düz metin değil (UTF-16 ya da ikili); UTF-8 olarak kaydedip tekrar yükleyin.")

        for kodlama in _KODLAMALAR:
            try:
                text = ham.decode(kodlama)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise IngestionError(
                "Metin kodlaması tanınmadı; dosyayı UTF-8 olarak kaydedip tekrar yükleyin.")

        title = os.path.splitext(os.path.basename(uri))[0]
        return Document(uri=uri, title=title, raw_text=text)
