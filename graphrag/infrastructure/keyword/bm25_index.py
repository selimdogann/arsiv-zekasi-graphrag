"""
InMemoryKeywordIndex — `IKeywordIndex`'in BM25 tabanlı bellek-içi uygulaması.

BM25, klasik anahtar-kelime sıralama algoritmasıdır: bir parçayı, sorgunun
kelimelerini içermesine göre puanlar — özellikle NADİR kelimeleri ödüllendirir
("proje" her yerde geçer, az bilgi; "Zeus" nadirdir, çok bilgi). Böylece özel
isimler, kodlar, TCKN gibi TAM terimleri kesin yakalar (vektör aramanın zayıf
olduğu yer).

Tokenizasyon Türkçe-farkındadır: `turkish_lower` ile küçültülür (İ/ı doğru),
sonra boşluklardan bölünür.
"""
from __future__ import annotations

from typing import Dict, List

from rank_bm25 import BM25Okapi

from graphrag.domain.entities import Chunk
from graphrag.domain.interfaces import IKeywordIndex
from graphrag.domain.text_tr import turkish_lower


class InMemoryKeywordIndex(IKeywordIndex):
    def __init__(self) -> None:
        self._chunks: Dict[str, Chunk] = {}      # chunk_id -> Chunk
        self._chunk_list: List[Chunk] = []
        self._bm25 = None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return turkish_lower(text).split()

    def index(self, chunks: List[Chunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk   # aynı id -> günceller (tekrarlanmaz)
        self._rebuild()

    def _rebuild(self) -> None:
        self._chunk_list = list(self._chunks.values())
        corpus = [self._tokenize(c.text) for c in self._chunk_list]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def delete_document(self, document_id: str) -> None:
        # chunk_id biçimi: "<belge_id>#<sıra>" — önek eşleşmesi yeterli.
        onek = document_id + "#"
        silinecek = [c for c in self._chunks if c.startswith(onek)]
        if not silinecek:
            return
        for chunk_id in silinecek:
            del self._chunks[chunk_id]
        self._rebuild()   # BM25 istatistikleri (kelime sıklıkları) yeniden hesaplanmalı

    def search(self, query: str, top_k: int):
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(self._tokenize(query))
        ranked = sorted(zip(self._chunk_list, scores),
                        key=lambda pair: pair[1], reverse=True)
        return ranked[:top_k]
