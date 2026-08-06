"""
Veritabanı motoru (engine) ve şema kurulumu.

Tek bir SQLAlchemy Engine oluşturur ve tabloları hazırlar. pgvector eklentisi
(docker/init.sql ile) zaten kurulu olsa da, güvenli olsun diye burada da
`CREATE EXTENSION IF NOT EXISTS vector` çalıştırılır.
"""
from __future__ import annotations

from sqlalchemy import Engine, create_engine, text

from graphrag.infrastructure.db.models import Base


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def init_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)

    # Küçük, idempotent şema geçişi: `relation` sütunu sonradan eklendi;
    # create_all mevcut tabloları değiştirmediği için burada garantilenir.
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE graph_edges "
            "ADD COLUMN IF NOT EXISTS relation VARCHAR DEFAULT ''"))
