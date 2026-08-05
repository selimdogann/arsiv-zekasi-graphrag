"""
Türkçe-farkında metin normalizasyonu.

Python'un varsayılan `str.lower()` metodu Türkçe için yanlış sonuç üretir
(İ/ı sorunu — bkz. proje notları). Bu modül, Türkçe kurallarına göre doğru
küçük harf katlaması yapar.
"""
from __future__ import annotations

_UP_TO_LOW = {"I": "ı", "İ": "i"}
# Küçük → büyük yönü (başlık biçimi için): 'i' → 'İ', 'ı' → 'I'
_LOW_TO_UP = {"i": "İ", "ı": "I"}


def turkish_lower(text: str) -> str:
    """Türkçe kurallı küçük harfe çevirir (I -> ı, İ -> i)."""
    for src, dst in _UP_TO_LOW.items():
        text = text.replace(src, dst)
    return text.lower()


def canonical_key(name: str) -> str:
    """İki farklı yazımı (örn. 'İzmir' ile 'IZMIR') aynı anahtara indirger."""
    return " ".join(turkish_lower(name).split())


# Şirket türü ekleri — varlık kimliğinin parçası değildir.
# "Gamma Danışmanlık" ile "Gamma Danışmanlık LTD. ŞTİ." aynı kurumdur.
_SIRKET_EKLERI = {
    "a.ş.", "a.ş", "aş", "a.s.", "as",
    "ltd.", "ltd", "şti.", "şti", "limited", "şirketi", "anonim",
    "inc.", "inc", "llc", "gmbh", "co.", "corp.",
}


def strip_company_suffix(name: str) -> str:
    """Sondaki şirket eklerini ('A.Ş.', 'LTD. ŞTİ.') temizler."""
    parcalar = name.strip().split()
    while parcalar and turkish_lower(parcalar[-1]).strip(",;:") in _SIRKET_EKLERI:
        parcalar.pop()
    return " ".join(parcalar) if parcalar else name.strip()


# Eşleştirme için Türkçe harf katlama tablosu.
# Amaç: aynı varlığın farklı yazımları tek anahtarda buluşsun —
#   · "ACME HOLDING" (noktasız I) ile "ACME HOLDİNG" (noktalı İ)
#   · Türkçe klavyesiz yazılan "Gamma Danismanlik" ile "Gamma Danışmanlık"
# Katlama YALNIZCA anahtar üretiminde kullanılır; gösterim etiketi bozulmaz.
_KATLAMA = str.maketrans({
    "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "â": "a", "î": "i",
})


def canonical_entity_key(name: str) -> str:
    """Varlık kimliği: şirket eki temizlenmiş, Türkçe normalize edilmiş ve
    aksan/İ-ı farkları katlanmış anahtar.

    'ACME HOLDİNG A.Ş.', 'ACME HOLDING', 'Acme Holding' → aynı anahtar.
    """
    return canonical_key(strip_company_suffix(name)).translate(_KATLAMA)


def turkish_title(name: str) -> str:
    """Türkçe kurallı başlık biçimi: 'ACME HOLDİNG' → 'Acme Holding'."""
    kelimeler = []
    for kelime in name.split():
        kucuk = turkish_lower(kelime)
        if not kucuk:
            continue
        ilk = _LOW_TO_UP.get(kucuk[0], kucuk[0].upper())
        kelimeler.append(ilk + kucuk[1:])
    return " ".join(kelimeler)


def display_label(name: str) -> str:
    """Gösterime uygun varlık etiketi: şirket eki temizlenir; TAMAMI BÜYÜK
    yazılmış çok kelimeli adlar okunaklı başlık biçimine çevrilir.

    Tek kelimelik büyük harfli adlar (kısaltmalar: TÜBİTAK, NATO) korunur.
    """
    ad = strip_company_suffix(name)
    if ad.isupper() and len(ad.split()) > 1:
        return turkish_title(ad)
    return ad


def prefer_label(mevcut: str, yeni: str) -> str:
    """Aynı varlığın iki yazımından, gösterime daha uygun olanı seçer.

    Tercih sırası: TAMAMI BÜYÜK olmayan, sonra daha kısa olan.
    ('ACME HOLDİNG' yerine 'Acme Holding' gösterilir.)
    """
    return min((mevcut, yeni), key=lambda s: (s.isupper(), len(s)))
