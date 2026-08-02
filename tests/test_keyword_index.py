"""
InMemoryKeywordIndex (BM25) için testler.

Anahtar-kelime araması deterministiktir (Ollama/embedding gerekmez), o yüzden
davranışı kesin test edebiliriz.
"""
from graphrag.domain.entities import Chunk
from graphrag.infrastructure.keyword.bm25_index import InMemoryKeywordIndex


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, text=text, embedding=())


def test_bm25_kelimenin_gectigi_parcayi_one_alir():
    idx = InMemoryKeywordIndex()
    idx.index([
        _chunk("1", "Acme Holding Proje Zeus ile anlaştı"),
        _chunk("2", "Deniz kenarında güzel bir tatil yapıldı"),
        _chunk("3", "Gamma Danışmanlık teknik destek verdi"),
    ])
    sonuc = idx.search("Proje Zeus", top_k=1)
    assert sonuc[0][0].chunk_id == "1"   # tam terim geçen parça ilk sırada


def test_bm25_bos_indeks_bos_liste_doner():
    idx = InMemoryKeywordIndex()
    assert idx.search("herhangi bir sorgu", top_k=3) == []


def test_bm25_turkce_buyuk_kucuk_harf_duyarsiz():
    idx = InMemoryKeywordIndex()
    idx.index([_chunk("1", "İstanbul Limanı raporu")])
    sonuc = idx.search("İSTANBUL", top_k=1)   # büyük harfle arasak da bulmalı
    assert len(sonuc) == 1
    assert sonuc[0][0].chunk_id == "1"


def test_bm25_ayni_id_tekrar_indekslenince_cogalmaz():
    idx = InMemoryKeywordIndex()
    idx.index([_chunk("1", "ilk sürüm metni")])
    idx.index([_chunk("1", "güncellenmiş metin")])   # aynı id
    sonuc = idx.search("metin", top_k=10)
    assert len(sonuc) == 1   # çoğalmadı, güncellendi
