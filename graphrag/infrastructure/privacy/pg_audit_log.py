"""
PostgresAuditLog — `IAuditLog`'un PostgreSQL uygulaması.

KVKK denetim kaydını kalıcı hâle getirir (yalnızca ekleme / append-only).
Veri minimizasyonu korunur: orijinal kişisel veri DEĞİL, sadece "hangi tip
veri, hangi placeholder ile, ne zaman maskelendi" saklanır.
"""
from __future__ import annotations

from typing import List

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from graphrag.domain.interfaces import IAuditLog
from graphrag.domain.privacy import AuditEvent, PIIType
from graphrag.infrastructure.db.models import AuditEventRow


class PostgresAuditLog(IAuditLog):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(self, event: AuditEvent) -> None:
        with Session(self._engine) as session:
            session.add(AuditEventRow(
                action=event.action,
                pii_type=event.pii_type.value,
                placeholder=event.placeholder,
                timestamp=event.timestamp,
            ))
            session.commit()

    def events(self) -> List[AuditEvent]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(AuditEventRow).order_by(AuditEventRow.id)).scalars().all()
            return [
                AuditEvent(action=r.action, pii_type=PIIType(r.pii_type),
                           placeholder=r.placeholder, timestamp=r.timestamp)
                for r in rows
            ]
