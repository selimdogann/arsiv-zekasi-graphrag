"""
SQLAlchemy ORM modelleri — Postgres tabloları.

Bunlar domain entity'lerinin (Chunk, GraphNode...) veritabanı karşılıklarıdır.
Domain saf kalsın diye ayrı tutulur: adaptörler bu satır (row) nesneleriyle
domain nesneleri arasında çeviri yapar.
"""
from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from graphrag.config import EMBED_DIM


class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, index=True)


class ChunkRow(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(String, index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(EMBED_DIM))


class GraphNodeRow(Base):
    __tablename__ = "graph_nodes"

    node_id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String)


class GraphEdgeRow(Base):
    __tablename__ = "graph_edges"

    # (source_id, target_id) bileşik birincil anahtar → aynı kenar tekrar
    # eklenince çoğalmaz, güncellenir (upsert).
    source_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    target_id: Mapped[str] = mapped_column(String, primary_key=True)
    weight: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String)
    pii_type: Mapped[str] = mapped_column(String)
    placeholder: Mapped[str] = mapped_column(String)
    timestamp: Mapped[str] = mapped_column(String)
