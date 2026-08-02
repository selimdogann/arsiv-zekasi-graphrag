"""
Türkçe-farkında metin normalizasyonu.

Python'un varsayılan `str.lower()` metodu Türkçe için yanlış sonuç üretir
(İ/ı sorunu — bkz. proje notları). Bu modül, Türkçe kurallarına göre doğru
küçük harf katlaması yapar.
"""
from __future__ import annotations

_UP_TO_LOW = {"I": "ı", "İ": "i"}


def turkish_lower(text: str) -> str:
    """Türkçe kurallı küçük harfe çevirir (I -> ı, İ -> i)."""
    for src, dst in _UP_TO_LOW.items():
        text = text.replace(src, dst)
    return text.lower()


def canonical_key(name: str) -> str:
    """İki farklı yazımı (örn. 'İzmir' ile 'IZMIR') aynı anahtara indirger."""
    return " ".join(turkish_lower(name).split())
