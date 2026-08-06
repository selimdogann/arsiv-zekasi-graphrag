"""
FilteredEntityExtractor — varlık çıkarımını GERÇEK adlandırılmış varlıklarla
(şirket, kişi, proje adı) sınırlayan süzgeç. Decorator desenidir: herhangi bir
`IEntityExtractor`'ı sarmalar, çıktısını eleyip geri verir.

Neden gerekli? LLM tabanlı çıkarım, metindeki her "önemli görünen" ifadeyi
döndürebiliyor: IBAN'lar, TCKN'ler, adresler, belge/referans kodları, tarihler,
"Sayın İlgili" gibi hitaplar ve "Teknik Gereksinim Analizi" gibi başlık
ifadeleri. Bunlar bilgi grafında düğüm olmamalı:

  - Analitik olarak değersizler (grafı şişirip bağlantı aramayı bozarlar).
  - KVKK açısından yanlışlar: IBAN/TCKN bir "varlık" değil, PII katmanında
    maskelenmesi gereken kişisel veridir.
"""
from __future__ import annotations

import re
from typing import List

from graphrag.domain.interfaces import IEntityExtractor
from graphrag.domain.text_tr import _KATLAMA, turkish_lower

# --- Biçimsel reddetme desenleri ---------------------------------------------

# KVKK maskeleme takma adları: [TCKN_1], [EMAIL_2] ...
# Köşeli parantezli ya da parantezsiz olabilir: "[TCKN_1]" veya "VKN_2"
_RE_PLACEHOLDER = re.compile(r"^\[?[A-Z]+_\d+\]?$")
# TCKN benzeri: 11 hane
_RE_TCKN = re.compile(r"^\d{11}$")
# IBAN: TR + rakam/boşluk dizisi
_RE_IBAN = re.compile(r"^TR[\s\d]{10,}$", re.IGNORECASE)
# Belge/referans kodu: DLT-2024-0053, SZL-2024-0417, GMM-FZB-2024-11
_RE_KOD = re.compile(r"^[A-ZÇĞİÖŞÜ]{2,}[-/][A-ZÇĞİÖŞÜ0-9]+([-/][A-ZÇĞİÖŞÜ0-9]+)*$")
# Yalnızca sayı/noktalama: "128", "7.", "2024"
_RE_SAYISAL = re.compile(r"^[\d\s.,:/()-]+$")

# --- Sözcüksel reddetme listeleri --------------------------------------------

# Tarih ifadeleri ("14 Mart 2024")
_AYLAR = ("ocak", "şubat", "mart", "nisan", "mayıs", "haziran",
          "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık")

# Adres bileşenleri
_ADRES = ("mahallesi", "mahalle", "caddesi", "cadde", "sokak", "sokağı",
          "bulvarı", "bulvar", "apartmanı", "sitesi", "plaza", "blok",
          "daire", "kat", "no:", "posta kodu")

# Hitap / nezaket kalıpları
_HITAP = ("sayın", "saygılarımızla", "saygılarımla", "değerli", "ilgili makama")

# Genel iş/belge terimi ekleri — özel isim değil, başlık ifadesidir.
# ("Teknik Gereksinim Analizi", "İnsan Kaynakları Departmanı", "Zaman Planı ...")
_GENEL_SON = ("analizi", "planı", "modeli", "takvimi", "raporu", "departmanı",
              "müdürlüğü", "müdürlük", "kurulu", "salonu", "projeleri", "projesi",
              "toplantısı", "sözleşmesi", "notu", "özeti", "hizmetleri", "süreci",
              "tutanağı", "yazışması", "maddesi", "bölümü", "listesi", "faaliyetleri",
              "birimi", "biriminin", "ekibi", "komitesi")

# Genel nitelemeyle başlayan ifadeler özel isim değildir:
# "Genel Müdürlük", "Sayın İlgili", "Tüm Birimler" ...
_GENEL_ON = ("genel", "sayın", "ilgili", "değerli", "tüm", "ilgili makam")

# Ülke / coğrafya adları — kurumsal arşiv analizinde varlık sayılmaz.
_COGRAFYA = ("türkiye", "turkiye", "türkiye cumhuriyeti", "istanbul",
             "ankara", "izmir", "avrupa", "asya", "amerika", "almanya",
             "ingiltere", "fransa", "türk", "t.c.", "tc")

# Kimlik/numara alanlarını bildiren terimler — bunlar PII katmanının işidir,
# grafta varlık olmamalıdır.
_KIMLIK_TERIMLERI = ("tckn", "vkn", "iban", "kimlik", "vergi", "sicil",
                     "numarası", "numara", "no", "nolu")

# Tek başına geçtiğinde varlık sayılmayan genel adlar
# ("Proje Zeus" geçerli; yalnız "Proje" değil).
_GENEL_TEKIL = ("müşteri", "musteri", "taraf", "taraflar", "şirket",
                "firma", "kurum", "sözleşme", "belge", "rapor", "proje",
                "yüklenici", "tedarikçi", "personel", "çalışan", "birim")

# Karşılaştırmalar katlanmış biçimde yapılır ("TÜRKİYE" = "TURKIYE")
_COGRAFYA_KATLI = {c.translate(_KATLAMA) for c in _COGRAFYA}
_GENEL_TEKIL_KATLI = {g.translate(_KATLAMA) for g in _GENEL_TEKIL}

# Bir varlık adı bu kadar kelimeden uzunsa büyük olasılıkla cümle/başlıktır.
_AZAMI_KELIME = 5


def _reddedilmeli(name: str) -> bool:
    """Verilen aday gerçek bir adlandırılmış varlık DEĞİL mi?"""
    ad = name.strip().strip(",;:.").strip('"\'«»')
    if len(ad) < 2:
        return True

    if (_RE_PLACEHOLDER.match(ad) or _RE_TCKN.match(ad)
            or _RE_IBAN.match(ad) or _RE_KOD.match(ad) or _RE_SAYISAL.match(ad)):
        return True

    # Cümle/etiketli ifade ("BİLGİ: ...", "Konu: ...") — özel isim değildir.
    if ":" in ad:
        return True

    kucuk = turkish_lower(ad)
    kelimeler = kucuk.split()

    # Uzun sayı dizisi içerenler kimlik/numara alanıdır ("VERGİ KİMLİK NO 4560123789")
    if any(len(k) >= 6 and k.isdigit() for k in kelimeler):
        return True
    # Kimlik/numara bildiren anahtar kelimeler
    if any(k in _KIMLIK_TERIMLERI for k in kelimeler):
        return True

    if len(kelimeler) > _AZAMI_KELIME:
        return True
    if kelimeler[0] in _HITAP or kelimeler[0] in _GENEL_ON:
        return True
    # Ülke/şehir adları (katlanmış karşılaştırma: 'TÜRKİYE' = 'TURKIYE')
    if kucuk.translate(_KATLAMA) in _COGRAFYA_KATLI:
        return True
    if any(k in _ADRES for k in kelimeler):
        return True
    if any(k in _AYLAR for k in kelimeler):
        return True
    if kelimeler[-1] in _GENEL_SON:
        return True
    # Tek kelimelik genel ad ("Müşteri", "Taraflar")
    if len(kelimeler) == 1 and kucuk.translate(_KATLAMA) in _GENEL_TEKIL_KATLI:
        return True

    # Harf içermeyen adaylar (ör. "2024-11") varlık olamaz.
    if not any(ch.isalpha() for ch in ad):
        return True
    return False


class FilteredEntityExtractor(IEntityExtractor):
    def __init__(self, inner: IEntityExtractor) -> None:
        self._inner = inner

    def extract(self, text: str) -> List[str]:
        return [ad for ad in self._inner.extract(text) if not _reddedilmeli(ad)]
