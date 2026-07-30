"""
SlidingWindowChunker için testler.

Chunking tamamen deterministiktir (aynı metin → hep aynı parçalar), bu yüzden
gerçek bir LLM'e ihtiyaç duymadan davranışını kesin olarak test edebiliriz.
"""
import pytest

from graphrag.infrastructure.chunking.text_chunker import SlidingWindowChunker


def test_kisa_metin_tek_parca():
    chunker = SlidingWindowChunker(chunk_size=500, overlap=50)
    assert chunker.chunk("kısa bir metin") == ["kısa bir metin"]


def test_bos_metin_bos_liste():
    chunker = SlidingWindowChunker()
    assert chunker.chunk("") == []
    assert chunker.chunk("   \n  \t ") == []


def test_uzun_metin_birden_fazla_parcaya_bolunur():
    chunker = SlidingWindowChunker(chunk_size=20, overlap=5)
    metin = " ".join(f"kelime{i}" for i in range(20))
    parcalar = chunker.chunk(metin)
    assert len(parcalar) > 1


def test_kelimeler_ortadan_bolunmez():
    chunker = SlidingWindowChunker(chunk_size=20, overlap=5)
    kelimeler = [f"kelime{i}" for i in range(20)]
    parcalar = chunker.chunk(" ".join(kelimeler))
    kelime_kumesi = set(kelimeler)
    for parca in parcalar:
        for token in parca.split():
            assert token in kelime_kumesi   # her token TAM bir orijinal kelime


def test_ardisik_parcalar_ortusur():
    chunker = SlidingWindowChunker(chunk_size=30, overlap=12)
    metin = " ".join(f"kelime{i}" for i in range(30))
    parcalar = chunker.chunk(metin)
    assert len(parcalar) >= 2
    for onceki, sonraki in zip(parcalar, parcalar[1:]):
        assert set(onceki.split()) & set(sonraki.split())   # ortak kelime var


def test_hicbir_kelime_kaybolmaz_ve_sira_korunur():
    chunker = SlidingWindowChunker(chunk_size=25, overlap=6)
    kelimeler = [f"k{i}" for i in range(40)]
    parcalar = chunker.chunk(" ".join(kelimeler))

    # Parçalardaki kelimeleri sırayla topla, örtüşme tekrarlarını at:
    gorulen = []
    for parca in parcalar:
        for token in parca.split():
            if token not in gorulen:
                gorulen.append(token)

    assert gorulen == kelimeler   # tümü, orijinal sırayla, eksiksiz


def test_gecersiz_parametreler_hata_firlatir():
    with pytest.raises(ValueError):
        SlidingWindowChunker(chunk_size=0)
    with pytest.raises(ValueError):
        SlidingWindowChunker(chunk_size=10, overlap=10)   # overlap < chunk_size olmalı
