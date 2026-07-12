"""
Türkçe-farkında metin normalizasyonu.

Python'un varsayılan `str.lower()/upper()` metotları Türkçe için yanlış
sonuç üretir (İ/ı sorunu — bkz. proje notları). Bu modül, Türkçe kurallarına
göre doğru büyük/küçük harf katlaması yapar.
"""
from __future__ import annotations

_UP_TO_LOW = {"I": "ı", "İ": "i"}
_LOW_TO_UP = {"i": "İ", "ı": "I"}


def turkish_lower(text: str) -> str:
    """Türkçe kurallı küçük harfe çevirir (I -> ı, İ -> i)."""
    for src, dst in _UP_TO_LOW.items():
        text = text.replace(src, dst)
    return text.lower()


def turkish_upper(text: str) -> str:
    """Türkçe kurallı büyük harfe çevirir (i -> İ, ı -> I)."""
    for src, dst in _LOW_TO_UP.items():
        text = text.replace(src, dst)
    return text.upper()


def canonical_key(name: str) -> str:
    """İki farklı yazımı (örn. 'İzmir' ile 'IZMIR') aynı anahtara indirger."""
    return " ".join(turkish_lower(name).split())
