"""
InMemoryVectorStore (kosinüs benzerliği) için testler.

Test vektörleri (2 boyutlu, elle hesaplanabilir açılarla):
  A = (1, 0)   B = (1, 1)   C = (0, 1)   D = (-1, 0)
A'ya göre beklenen benzerlik sıralaması: A(1.0) > B(~0.71) > C(0.0) > D(-1.0)
"""
import pytest

from graphrag.domain.entities import Chunk
from graphrag.infrastructure.vector.vector_store import InMemoryVectorStore


def _kurulu_depo():
    store = InMemoryVectorStore()
    store.upsert([
        Chunk(chunk_id="A", text="A", embedding=(1.0, 0.0)),
        Chunk(chunk_id="B", text="B", embedding=(1.0, 1.0)),
        Chunk(chunk_id="C", text="C", embedding=(0.0, 1.0)),
        Chunk(chunk_id="D", text="D", embedding=(-1.0, 0.0)),
    ])
    return store


def test_ozdes_vektor_tam_benzer():
    store = _kurulu_depo()
    sonuclar = store.search(query_embedding=(1.0, 0.0), top_k=4)
    en_iyi_chunk, en_iyi_skor = sonuclar[0]
    assert en_iyi_chunk.chunk_id == "A"
    assert en_iyi_skor == pytest.approx(1.0, abs=0.001)


def test_dik_vektor_alakasiz_sayilir():
    store = _kurulu_depo()
    sonuclar = {chunk.chunk_id: skor
                for chunk, skor in store.search((1.0, 0.0), top_k=4)}
    assert sonuclar["C"] == pytest.approx(0.0, abs=0.001)


def test_ters_vektor_negatif_benzerlik_verir():
    store = _kurulu_depo()
    sonuclar = {chunk.chunk_id: skor
                for chunk, skor in store.search((1.0, 0.0), top_k=4)}
    assert sonuclar["D"] == pytest.approx(-1.0, abs=0.001)


def test_siralama_benzerlige_gore_azalan():
    store = _kurulu_depo()
    sonuclar = store.search((1.0, 0.0), top_k=4)
    sirali_id = [chunk.chunk_id for chunk, _ in sonuclar]
    assert sirali_id == ["A", "B", "C", "D"]


def test_top_k_sonuc_sayisini_sinirlar():
    store = _kurulu_depo()
    sonuclar = store.search((1.0, 0.0), top_k=2)
    assert len(sonuclar) == 2
