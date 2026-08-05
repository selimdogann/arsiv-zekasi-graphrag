"""
KvkkPiiRedactor — regex + checksum tabanlı KVKK (6698 sayılı Kanun) maskeleme.

Kişisel veriyi SİLMEK yerine "takma adlaştırma" (pseudonymization) kullanır:
aynı değer HER ZAMAN aynı takma adı (örn. "[TCKN_1]") alır — bu sayede "aynı
kişiden bahseden belgeleri bul" gibi analiz korunurken, ham kişisel veri
hiçbir yerde (ne indekste, ne grafta, ne denetim kaydında) açıkça saklanmaz.

Tespit stratejisi (yanlış-pozitif ile yanlış-negatif dengesi):
  - TCKN / VKN — BAĞLAM ETİKETLİ: "T.C. Kimlik No: 12345678901",
    "Vergi Kimlik Numarası 4560123789". Etiket verinin ne olduğunu zaten
    söylediği için checksum aranmaz.
  - TCKN — BAĞLAMSIZ: 11 haneli adaylar `is_valid_tckn` ile DOĞRULANIR; böylece
    rastgele 11 haneli bir sayı (örn. sözleşme numarası) yanlışlıkla maskelenmez.
  - IBAN: "TR + 24 rakam" biçimi tek başına belirleyicidir, bağlam gerekmez.
    Sağlama tutmasa bile maskelenir — KVKK'da kişisel veriyi kaçırmak,
    fazladan maskelemekten daha ağır bir risktir.
  - E-posta / telefon: basit ama pratik regex desenleriyle yakalanır.

NOT: Bu katman, varlık çıkarımından ÖNCE çalışır (bkz. GraphRAGCore.ingest).
Kişisel veriler bu yüzden hem maskelenir hem denetim kaydına yazılır; ayrıca
`FilteredEntityExtractor` sayesinde grafa varlık olarak da girmezler.
"""
from __future__ import annotations

import re
from typing import Dict, Tuple

from graphrag.domain.interfaces import IAuditLog, IPrivacyFilter
from graphrag.domain.privacy import AuditEvent, PIIType
from graphrag.infrastructure.nlp.tr_validators import is_valid_tckn

_RE_ELEVEN_DIGITS = re.compile(r"\b\d{11}\b")
_RE_EMAIL = re.compile(r"\b[\w.\-]+@[\w.\-]+\.\w+\b")
_RE_PHONE = re.compile(r"\b0?5\d{2}[\s.\-]?\d{3}[\s.\-]?\d{2}[\s.\-]?\d{2}\b")

# --- Bağlam etiketli kimlik numaraları ---
# Belgelerde numaralar çoğunlukla etiketiyle geçer: "T.C. Kimlik No: 12345678901",
# "Vergi Kimlik Numarası 4560123789". Etiket varsa checksum'a bakılmaz —
# etiket, verinin ne olduğunu zaten açıkça söyler. Bu, sınama/örnek belgelerdeki
# checksum'ı tutmayan numaraların maskelenmeden kalmasını önler.
_KIMLIK = r"[Kk][iıİI][Mm][Ll][iıİI][Kk]"
_NO = r"(?:[Nn][Oo]|[Nn][Uu][Mm][Aa][Rr][Aa][Ss][iıİI])"
_RE_TCKN_ETIKETLI = re.compile(
    rf"(?:[Tt]\.?\s*[CcÇç]\.?\s*)?{_KIMLIK}\s*{_NO}\s*[:.]?\s*(\d{{11}})\b")
_RE_VKN_ETIKETLI = re.compile(
    rf"[Vv][Ee][Rr][Gg][iıİI]\s*{_KIMLIK}\s*{_NO}\s*[:.]?\s*(\d{{10}})\b")

# IBAN kendi kendini tanımlar (TR öneki + mod-97 sağlaması); bağlam gerekmez.
_RE_IBAN = re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b")


class KvkkPiiRedactor(IPrivacyFilter):
    def __init__(self, audit_log: IAuditLog) -> None:
        self._audit_log = audit_log
        # (tip, orijinal_değer) -> takma ad — kararlı eşleme (pseudonym vault)
        self._vault: Dict[Tuple[PIIType, str], str] = {}
        self._counters: Dict[PIIType, int] = {}

    def _placeholder_for(self, pii_type: PIIType, original: str) -> str:
        key = (pii_type, original)
        existing = self._vault.get(key)
        if existing is not None:
            return existing  # aynı değer -> aynı takma ad (kararlılık)

        self._counters[pii_type] = self._counters.get(pii_type, 0) + 1
        placeholder = f"[{pii_type.value}_{self._counters[pii_type]}]"
        self._vault[key] = placeholder
        self._audit_log.record(AuditEvent(
            action="REDACT", pii_type=pii_type, placeholder=placeholder))
        return placeholder

    def _mask_group(self, match: "re.Match[str]", pii_type: PIIType) -> str:
        """Etiketli desende YALNIZCA numara kısmını takma adla değiştirir
        ('T.C. Kimlik No: 123...' → 'T.C. Kimlik No: [TCKN_1]')."""
        value = match.group(1)
        return match.group(0).replace(value, self._placeholder_for(pii_type, value))

    def redact(self, text: str) -> str:
        def _redact_tckn(match: "re.Match[str]") -> str:
            value = match.group(0)
            if is_valid_tckn(value):
                return self._placeholder_for(PIIType.TCKN, value)
            return value  # checksum geçmedi -> TCKN değil, dokunma

        def _redact_iban(match: "re.Match[str]") -> str:
            # IBAN biçimi (TR + 24 rakam) tek başına belirleyicidir; sağlama
            # tutmasa bile maskelenir. KVKK'da kişisel veriyi kaçırmak,
            # fazladan maskelemekten daha ağır bir risktir.
            value = match.group(0)
            return self._placeholder_for(PIIType.IBAN, value.replace(" ", ""))

        # Sıra önemli: önce kendi kendini tanımlayan IBAN, sonra etiketli
        # kimlik numaraları, en sonra bağlamsız (checksum'lı) TCKN adayları.
        text = _RE_IBAN.sub(_redact_iban, text)
        text = _RE_TCKN_ETIKETLI.sub(lambda m: self._mask_group(m, PIIType.TCKN), text)
        text = _RE_VKN_ETIKETLI.sub(lambda m: self._mask_group(m, PIIType.VKN), text)
        text = _RE_ELEVEN_DIGITS.sub(_redact_tckn, text)
        text = _RE_EMAIL.sub(
            lambda m: self._placeholder_for(PIIType.EMAIL, m.group(0)), text)
        text = _RE_PHONE.sub(
            lambda m: self._placeholder_for(PIIType.PHONE, m.group(0)), text)
        return text
