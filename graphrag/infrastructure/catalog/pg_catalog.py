"""
PostgresDocumentCatalog — `IDocumentCatalog`'un PostgreSQL uygulaması.

Belge kaydını kalıcı hâle getirir: sunucu yeniden başlasa bile arayüzdeki
belge listesi ve kaynak gösterimindeki belge adları korunur.
"""
from __future__ import annotations

from typing import List

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from graphrag.domain.entities import DocumentInfo
from graphrag.domain.interfaces import IDocumentCatalog
from graphrag.infrastructure.db.models import DocumentRow


class PostgresDocumentCatalog(IDocumentCatalog):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, info: DocumentInfo) -> None:
        with Session(self._engine) as session:
            session.merge(DocumentRow(
                document_id=info.document_id,
                name=info.name,
                state=info.state,
                created_at=info.created_at,
            ))
            session.commit()

    def all(self) -> List[DocumentInfo]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(DocumentRow).order_by(DocumentRow.created_at.desc())
            ).scalars().all()
            return [
                DocumentInfo(document_id=r.document_id, name=r.name,
                             state=r.state, created_at=r.created_at)
                for r in rows
            ]

    def remove(self, document_id: str) -> None:
        with Session(self._engine) as session:
            session.execute(
                delete(DocumentRow).where(DocumentRow.document_id == document_id))
            session.commit()
