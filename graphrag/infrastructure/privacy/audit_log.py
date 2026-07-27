"""
InMemoryAuditLog — `IAuditLog`'un bellek-içi, append-only uygulaması.

Denetim kaydı YALNIZCA tip/takma-ad/zaman tutar; orijinal kişisel veriyi
ASLA saklamaz (veri minimizasyonu) — bkz. `AuditEvent` tanımı.
"""
from __future__ import annotations

from typing import List

from graphrag.domain.interfaces import IAuditLog
from graphrag.domain.privacy import AuditEvent


class InMemoryAuditLog(IAuditLog):
    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self._events.append(event)

    def events(self) -> List[AuditEvent]:
        return list(self._events)
