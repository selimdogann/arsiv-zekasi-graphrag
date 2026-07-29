"""
KvkkPiiRedactor için testler.

Kontrol ettiklerimiz:
  - Geçerli bir TCKN maskelenir (checksum'dan geçtiği için)
  - Geçersiz (checksum'ı tutmayan) 11 haneli bir sayı DOKUNULMADAN kalır
  - Aynı değer HER ZAMAN aynı takma adı alır (pseudonym kararlılığı)
  - E-posta ve telefon da maskelenir
  - Denetim kaydı, orijinal DEĞERİ asla saklamaz (sadece tip + takma ad)
"""
from graphrag.domain.privacy import PIIType
from graphrag.infrastructure.privacy.audit_log import InMemoryAuditLog
from graphrag.infrastructure.privacy.kvkk_redactor import KvkkPiiRedactor


def _kurulu_maskeleyici():
    audit = InMemoryAuditLog()
    redactor = KvkkPiiRedactor(audit)
    return redactor, audit


def test_gecerli_tckn_maskelenir():
    redactor, _ = _kurulu_maskeleyici()
    sonuc = redactor.redact("TC kimlik no: 10000000146")
    assert "10000000146" not in sonuc
    assert "[TCKN_1]" in sonuc


def test_gecersiz_tckn_dokunulmadan_kalir():
    redactor, _ = _kurulu_maskeleyici()
    # 11 haneli ama checksum'ı tutmayan bir sayı (örn. bir sözleşme no'su olabilir)
    sonuc = redactor.redact("Sözleşme no: 12345678901")
    assert "12345678901" in sonuc


def test_ayni_tckn_ayni_takma_adi_alir():
    redactor, _ = _kurulu_maskeleyici()
    sonuc1 = redactor.redact("Kişi: 10000000146")
    sonuc2 = redactor.redact("Tekrar: 10000000146")
    assert "[TCKN_1]" in sonuc1
    assert "[TCKN_1]" in sonuc2  # yeni bir [TCKN_2] DEĞİL, aynısı


def test_email_maskelenir():
    redactor, _ = _kurulu_maskeleyici()
    sonuc = redactor.redact("İletişim: ali@example.com")
    assert "ali@example.com" not in sonuc
    assert "[EMAIL_1]" in sonuc


def test_telefon_maskelenir():
    redactor, _ = _kurulu_maskeleyici()
    sonuc = redactor.redact("Telefon: 05321234567")
    assert "05321234567" not in sonuc
    assert "[PHONE_1]" in sonuc


def test_denetim_kaydi_orijinal_degeri_saklamaz():
    redactor, audit = _kurulu_maskeleyici()
    redactor.redact("TC kimlik no: 10000000146")
    olaylar = audit.events()
    assert len(olaylar) == 1
    assert olaylar[0].pii_type == PIIType.TCKN
    assert olaylar[0].placeholder == "[TCKN_1]"
    # AuditEvent'in hiçbir alanında "10000000146" GEÇMEMELİ:
    assert "10000000146" not in str(olaylar[0])
