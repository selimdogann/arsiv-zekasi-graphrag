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


# ---------------------------------------- bağlam etiketli kimlikler + IBAN/VKN

def test_etiketli_tckn_checksum_gecmese_de_maskelenir():
    # "T.C. Kimlik No:" etiketi verinin ne olduğunu zaten söyler
    log = InMemoryAuditLog()
    sonuc = KvkkPiiRedactor(log).redact("Zeynep Demir (T.C. Kimlik No: 12345678901)")
    assert "12345678901" not in sonuc
    assert "[TCKN_1]" in sonuc
    assert log.events()[0].pii_type.value == "TCKN"


def test_etiketli_vkn_maskelenir():
    log = InMemoryAuditLog()
    sonuc = KvkkPiiRedactor(log).redact("Vergi Kimlik Numarası 4560123789 olup")
    assert "4560123789" not in sonuc
    assert "[VKN_1]" in sonuc
    assert log.events()[0].pii_type.value == "VKN"


def test_iban_maskelenir():
    log = InMemoryAuditLog()
    sonuc = KvkkPiiRedactor(log).redact("Hesap: TR33 0006 1005 1978 6457 8413 26")
    assert "TR33" not in sonuc
    assert "[IBAN_1]" in sonuc
    assert log.events()[0].pii_type.value == "IBAN"


def test_gecersiz_saglamali_iban_de_maskelenir():
    # Biçim belirleyicidir; kişisel veriyi kaçırmamak esastır
    log = InMemoryAuditLog()
    sonuc = KvkkPiiRedactor(log).redact("Hesap: TR12 0001 0002 0003 0004 0005 06")
    assert "[IBAN_1]" in sonuc


def test_etiket_metni_korunur_sadece_numara_maskelenir():
    log = InMemoryAuditLog()
    sonuc = KvkkPiiRedactor(log).redact("T.C. Kimlik No: 12345678901")
    assert sonuc.startswith("T.C. Kimlik No: ")   # etiket yerinde
    assert sonuc.endswith("[TCKN_1]")


def test_siradan_11_haneli_sayi_etiketsiz_dokunulmaz():
    # Bağlamsız ve checksum'ı tutmayan sayı maskelenmemeli
    log = InMemoryAuditLog()
    sonuc = KvkkPiiRedactor(log).redact("Belge referansı 12345678901 şeklindedir.")
    assert "12345678901" in sonuc
    assert log.events() == []
