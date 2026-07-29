"""
tr_validators.py için otomatik testler.

Her fonksiyonun HEM geçerli HEM geçersiz örneklerle doğru davrandığını kontrol
eder. `assert` = "şu sonucu bekliyorum, değilse testi kır."
"""
from graphrag.infrastructure.nlp.tr_validators import (
    is_valid_tckn,
    is_valid_vkn,
    is_valid_iban_tr,
)


def test_gecerli_tckn_kabul_edilir():
    assert is_valid_tckn("10000000146") is True


def test_bozuk_tckn_reddedilir():
    assert is_valid_tckn("10000000145") is False   # son hane bozuk


def test_yanlis_uzunluktaki_tckn_reddedilir():
    assert is_valid_tckn("123") is False            # 11 hane değil


def test_gecerli_vkn_kabul_edilir():
    assert is_valid_vkn("1234567890") is True


def test_bozuk_vkn_reddedilir():
    assert is_valid_vkn("1234567891") is False


def test_gecerli_iban_kabul_edilir():
    assert is_valid_iban_tr("TR330006100519786457841326") is True


def test_bozuk_iban_reddedilir():
    assert is_valid_iban_tr("TR330006100519786457841327") is False
