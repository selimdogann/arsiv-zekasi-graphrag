"""
FilteredEntityExtractor için testler.

Sahte bir çıkarıcıya gerçek belgelerden gözlenmiş "çöp" adaylar verilir;
süzgecin bunları eleyip yalnızca gerçek adlandırılmış varlıkları bırakması
beklenir.
"""
from graphrag.domain.interfaces import IEntityExtractor
from graphrag.infrastructure.nlp.entity_filter import FilteredEntityExtractor


class _SabitCikarici(IEntityExtractor):
    def __init__(self, adlar):
        self._adlar = adlar

    def extract(self, text):
        return list(self._adlar)


def _suz(adlar):
    return FilteredEntityExtractor(_SabitCikarici(adlar)).extract("...")


def test_gercek_varliklar_korunur():
    adlar = ["Acme Holding", "Proje Zeus", "Gamma Danışmanlık LTD. ŞTİ.",
             "Delta Yazılım A.Ş.", "Ayşe Yıldız", "Zeynep Demir"]
    assert _suz(adlar) == adlar


def test_iban_ve_tckn_elenir():
    # KVKK ürününde IBAN/TCKN varlık değildir; PII katmanında maskelenir.
    adlar = ["TR33 0006 1005 1978 6457 8413 26", "10000000146", "Acme Holding"]
    assert _suz(adlar) == ["Acme Holding"]


def test_kvkk_takma_adlari_elenir():
    assert _suz(["[TCKN_1]", "[EMAIL_2]", "Proje Zeus"]) == ["Proje Zeus"]


def test_referans_kodlari_elenir():
    adlar = ["DLT-2024-0053", "SZL-2024-0417", "GMM-FZB-2024-11", "Delta Lojistik"]
    assert _suz(adlar) == ["Delta Lojistik"]


def test_adresler_elenir():
    adlar = ["Maslak Mahallesi Büyükdere Caddesi No: 128", "Acme Holding"]
    assert _suz(adlar) == ["Acme Holding"]


def test_hitap_kaliplari_elenir():
    assert _suz(["Sayın İlgili", "Saygılarımızla", "Zeynep Demir"]) == ["Zeynep Demir"]


def test_baslik_ifadeleri_elenir():
    # Özel isim değil, belge başlığı/bölüm adı olan ifadeler
    adlar = ["Teknik Gereksinim Analizi", "Zaman Planı ve Teslim Takvimi",
             "İnsan Kaynakları Departmanı", "YÖNLENDİRME KURULU",
             "Kurumsal Dijital Dönüşüm Projeleri", "Proje Zeus"]
    assert _suz(adlar) == ["Proje Zeus"]


def test_tarih_ve_salt_sayi_elenir():
    assert _suz(["14 Mart 2024", "128", "2024", "Acme Holding"]) == ["Acme Holding"]


def test_cok_uzun_ifadeler_elenir():
    uzun = "Genel Müdürlük Binası Yedinci Kat Büyük Toplantı Salonu Girişi"
    assert _suz([uzun, "Acme Holding"]) == ["Acme Holding"]


def test_genel_birim_adlari_elenir():
    # "Genel Müdürlük" bir özel isim değil, genel bir birim adıdır
    adlar = ["Genel Müdürlük", "Genel Mühürlük", "Tüm Birimler", "Acme Holding"]
    assert _suz(adlar) == ["Acme Holding"]


def test_etiketli_cumleler_elenir():
    # LLM bazen kendi yanıt kalıbını varlık gibi döndürebiliyor
    adlar = ["BİLGİ: Bu bilgi arşivde bulunamadı.", "Konu: İş Birliği", "Proje Zeus"]
    assert _suz(adlar) == ["Proje Zeus"]


def test_kimlik_numarasi_alanlari_elenir():
    adlar = ["VERGİ KİMLİK NUMARASI 4560123789", "Sicil No 12345678",
             "Delta Yazılım"]
    assert _suz(adlar) == ["Delta Yazılım"]


def test_genel_birim_ekleri_elenir():
    assert _suz(["İş Geliştirme Birimi", "Proje Ekibi", "Acme Holding"]) == ["Acme Holding"]
