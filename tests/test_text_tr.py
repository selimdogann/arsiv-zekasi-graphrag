"""
text_tr.py için testler — Türkçe İ/ı düzeltmesinin doğru çalıştığını kanıtlar.
"""
from graphrag.domain.text_tr import (
    canonical_entity_key,
    canonical_key,
    display_label,
    locate_in_source,
    prefer_label,
    strip_company_suffix,
    turkish_lower,
)


def test_buyuk_I_kucuk_noktasiz_olur():
    assert turkish_lower("IRMAK") == "ırmak"


def test_buyuk_noktali_I_kucuk_i_olur():
    assert turkish_lower("İZMİR") == "izmir"


def test_farkli_yazimlar_ayni_anahtara_iner():
    # "İzmir Limanı" ile "İZMİR LİMANI" (doğru TR büyük harf) aynı varlık sayılmalı
    assert canonical_key("İzmir Limanı") == canonical_key("İZMİR LİMANI")


# --------------------------------------------- şirket eki temizliği / birleştirme

def test_sirket_ekleri_temizlenir():
    assert strip_company_suffix("Gamma Danışmanlık LTD. ŞTİ.") == "Gamma Danışmanlık"
    assert strip_company_suffix("Delta Yazılım A.Ş.") == "Delta Yazılım"
    assert strip_company_suffix("Acme Holding") == "Acme Holding"


def test_ayni_kurum_tek_anahtarda_birlesir():
    # Farklı yazım + şirket eki + Türkçe büyük harf → aynı varlık
    assert canonical_entity_key("ACME HOLDİNG A.Ş.") == canonical_entity_key("Acme Holding")
    assert (canonical_entity_key("Gamma Danışmanlık LTD. ŞTİ.")
            == canonical_entity_key("Gamma Danışmanlık"))


def test_farkli_kurumlar_ayri_kalir():
    assert canonical_entity_key("Acme Holding") != canonical_entity_key("Delta Lojistik")


def test_gosterim_etiketi_okunakli_olani_secer():
    # TAMAMI BÜYÜK yazım yerine normal yazım tercih edilir
    assert prefer_label("ACME HOLDİNG", "Acme Holding") == "Acme Holding"
    assert prefer_label("Acme Holding", "ACME HOLDİNG") == "Acme Holding"


def test_tamami_buyuk_adlar_okunakli_hale_gelir():
    assert display_label("ACME HOLDİNG A.Ş.") == "Acme Holding"
    assert display_label("GAMMA DANIŞMANLIK LTD. ŞTİ.") == "Gamma Danışmanlık"


def test_tek_kelimelik_kisaltmalar_korunur():
    # TÜBİTAK gibi kısaltmalar başlık biçimine çevrilmemeli
    assert display_label("TÜBİTAK") == "TÜBİTAK"


def test_normal_yazim_degismez():
    assert display_label("Acme Holding") == "Acme Holding"


def test_noktali_noktasiz_I_ayni_anahtarda_bulusur():
    # LLM bazen "İ"yi "I" olarak döndürüyor; ikisi aynı varlık olmalı
    assert canonical_entity_key("ACME HOLDING") == canonical_entity_key("ACME HOLDİNG")
    assert canonical_entity_key("ACME HOLDING") == canonical_entity_key("Acme Holding")


def test_turkce_klavyesiz_yazim_ayni_anahtara_iner():
    # Kullanıcı "Gamma Danismanlik" yazsa da doğru varlığı bulmalı
    assert (canonical_entity_key("Gamma Danismanlik")
            == canonical_entity_key("Gamma Danışmanlık"))


# ------------------------------------------------ kaynağa sabitleme / temellendirme

_BELGE = "Taraflar ACME HOLDİNG A.Ş. ile GAMMA DANIŞMANLIK arasında anlaştı."


def test_ad_belgedeki_yazima_sabitlenir():
    # LLM "İ"yi "I" olarak döndürse bile belgedeki yazım kullanılır
    assert locate_in_source("ACME HOLDING", _BELGE) == "ACME HOLDİNG"


def test_farkli_buyuk_kucuk_yazim_da_bulunur():
    assert locate_in_source("Gamma Danışmanlık", _BELGE) == "GAMMA DANIŞMANLIK"


def test_belgede_gecmeyen_ad_none_doner():
    # LLM uydurması (belgede karşılığı yok) → grafa alınmamalı
    assert locate_in_source("Delta Lojistik", _BELGE) is None


def test_llm_kopyalama_gurultusu_belgedeki_yazima_duzeltilir():
    # Yerel LLM Türkçe metni bozuk kopyalayabiliyor; yakın eşleşme düzeltir
    assert locate_in_source("ACME HOLDİNİNG A.Ş.", _BELGE) == "ACME HOLDİNG A.Ş."
