"""
text_tr.py için testler — Türkçe İ/ı düzeltmesinin doğru çalıştığını kanıtlar.
"""
from graphrag.domain.text_tr import turkish_lower, canonical_key


def test_buyuk_I_kucuk_noktasiz_olur():
    assert turkish_lower("IRMAK") == "ırmak"


def test_buyuk_noktali_I_kucuk_i_olur():
    assert turkish_lower("İZMİR") == "izmir"


def test_farkli_yazimlar_ayni_anahtara_iner():
    # "İzmir Limanı" ile "İZMİR LİMANI" (doğru TR büyük harf) aynı varlık sayılmalı
    assert canonical_key("İzmir Limanı") == canonical_key("İZMİR LİMANI")
