"""
KVKK (6698 sayılı Kanun) / PII domain modelleri.

Kişisel veriyi silmek yerine "takma adlaştırma" (pseudonymization) kullanılır:
veri, YETKİLİ erişimle geri çözülebilen kararlı bir belirteçle (örn.
"[PERSON_1]") değiştirilir. Böylece "aynı kişiden bahseden belgeleri bul" gibi
analiz korunurken, ham kişisel veri hiçbir yerde açıkça saklanmaz.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PIIType(str, Enum):
    """KVKK kapsamındaki kişisel veri kategorileri."""

    PERSON = "PERSON"
    TCKN = "TCKN"
    PHONE = "PHONE"
    EMAIL = "EMAIL"


@dataclass(frozen=True)
class PIIMatch:
    """Metinde tespit edilmiş tek bir kişisel veri örneği."""

    type: PIIType
    original: str
    placeholder: str


@dataclass(frozen=True)
class AuditEvent:
    """Denetim kaydı. Orijinal DEĞERİ asla saklamaz (veri minimizasyonu)."""

    action: str  # "REDACT" | "DEANONYMIZE"
    pii_type: PIIType
    placeholder: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
