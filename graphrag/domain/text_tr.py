"""
Türkçe-farkında metin normalizasyonu.

Python'un varsayılan `str.lower()` metodu Türkçe için yanlış sonuç üretir
(İ/ı sorunu — bkz. proje notları). Bu modül, Türkçe kurallarına göre doğru
küçük harf katlaması yapar.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

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


def _fold(text: str) -> str:
    """Eşleştirme için katlanmış biçim (küçük harf + aksan/İ-ı katlama)."""
    return turkish_lower(text).translate(_KATLAMA)


# Belgedeki "ad adayı" örüntüsü: büyük harfle başlayan kelime dizileri
# ("ACME HOLDİNG A.Ş.", "Proje Zeus", "Ayşe Yıldız").
_RE_AD_ADAYI = re.compile(
    r"[A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü.]*(?:\s+[A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü.]*){0,4}")

# Yakın eşleşme eşiği: LLM'in kopyalama gürültüsünü toleranslar
# ("ACME HOLDİNİNG" → "ACME HOLDİNG"), ama farklı varlıkları birleştirmez.
_BENZERLIK_ESIGI = 0.82


def _ad_adaylari(source_text: str):
    """Belgedeki ad adaylarını üretir.

    Büyük harfle başlayan her kelime dizisinin YALNIZCA tamamı değil, ardışık
    alt pencereleri de aday sayılır. Aksi hâlde cümle başındaki büyük harfli
    kelime adı yutuyordu: "Taraflar ACME HOLDİNG A.Ş." tek aday olunca
    "ACME HOLDİNG A.Ş." hiç aday listesine girmiyordu.
    """
    adaylar = []
    for dizi in _RE_AD_ADAYI.finditer(source_text):
        metin = dizi.group(0)
        kelimeler = [(m.start(), m.end()) for m in re.finditer(r"\S+", metin)]
        for i in range(len(kelimeler)):
            for j in range(i, min(i + 5, len(kelimeler))):
                adaylar.append(metin[kelimeler[i][0]:kelimeler[j][1]])
    return adaylar


def locate_in_source(name: str, source_text: str, esik: float = _BENZERLIK_ESIGI):
    """Varlık adını kaynak belgede arar; bulursa BELGEDEKİ yazımı, bulamazsa
    `None` döndürür.

    İki işi birden yapar:
      1. **Kaynağa sabitleme.** LLM belgedeki 'ACME HOLDİNG'i 'ACME HOLDING'
         (noktasız I) diye döndürebiliyor; Türkçe küçültme kuralı gereği bu
         'holdıng' bozulmasına yol açıyordu. Belgedeki yazım esas alınır.
      2. **Temellendirme (grounding).** Belgede karşılığı olmayan bir ad,
         LLM'in uydurmasıdır ve grafa alınmamalıdır.

    Karşılaştırma katlanmış yapılır (büyük/küçük harf, aksan, İ/ı yok sayılır).
    Birebir bulunamazsa, belgedeki ad adaylarıyla YAKIN eşleşme aranır — çünkü
    yerel LLM Türkçe metni bazen bozuk kopyalıyor ("MAHALLESİ" → "MAHALELİSİ").
    """
    if not name or not source_text:
        return None

    katlanmis_ad, katlanmis_metin = _fold(name), _fold(source_text)
    # Katlama karakter sayısını korumazsa dizin hizası bozulur; güvenli tarafta kal.
    if len(katlanmis_ad) != len(name) or len(katlanmis_metin) != len(source_text):
        return name

    # 1) Birebir (katlanmış) eşleşme
    i = katlanmis_metin.find(katlanmis_ad)
    if i != -1:
        return source_text[i:i + len(name)]

    # 2) Yakın eşleşme: belgedeki ad adayları arasında en benzerini bul
    en_iyi, en_iyi_oran = None, 0.0
    for aday in _ad_adaylari(source_text):
        oran = SequenceMatcher(None, katlanmis_ad, _fold(aday)).ratio()
        if oran > en_iyi_oran:
            en_iyi, en_iyi_oran = aday, oran
    return en_iyi if en_iyi_oran >= esik else None


def prefer_label(mevcut: str, yeni: str) -> str:
    """Aynı varlığın iki yazımından, gösterime daha uygun olanı seçer.

    Tercih sırası: TAMAMI BÜYÜK olmayan, sonra daha kısa olan.
    ('ACME HOLDİNG' yerine 'Acme Holding' gösterilir.)
    """
    return min((mevcut, yeni), key=lambda s: (s.isupper(), len(s)))
