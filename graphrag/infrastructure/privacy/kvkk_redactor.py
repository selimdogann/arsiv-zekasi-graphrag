"""
KvkkPiiRedactor — regex + checksum tabanlı KVKK (6698 sayılı Kanun) maskeleme.

Kişisel veriyi SİLMEK yerine "takma adlaştırma" (pseudonymization) kullanır:
aynı değer HER ZAMAN aynı takma adı (örn. "[TCKN_1]") alır — bu sayede "aynı
kişiden bahseden belgeleri bul" gibi analiz korunurken, ham kişisel veri
hiçbir yerde (ne indekste, ne grafta, ne denetim kaydında) açıkça saklanmaz.

Tespit stratejisi:
  - TCKN: 11 haneli adaylar, `tr_validators.is_valid_tckn` ile DOĞRULANIR
    (rastgele 11 haneli bir sayı — örn. bir sözleşme numarası — yanlışlıkla
    maskelenmez; yalnızca checksum'ı geçen GERÇEK bir TCKN maskelenir).
  - E-posta / telefon: basit ama pratik regex desenleriyle yakalanır.
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

    def redact(self, text: str) -> str:
        def _redact_tckn(match: "re.Match[str]") -> str:
            value = match.group(0)
            if is_valid_tckn(value):
                return self._placeholder_for(PIIType.TCKN, value)
            return value  # checksum geçmedi -> TCKN değil, dokunma

        text = _RE_ELEVEN_DIGITS.sub(_redact_tckn, text)
        text = _RE_EMAIL.sub(
            lambda m: self._placeholder_for(PIIType.EMAIL, m.group(0)), text)
        text = _RE_PHONE.sub(
            lambda m: self._placeholder_for(PIIType.PHONE, m.group(0)), text)
        return text
