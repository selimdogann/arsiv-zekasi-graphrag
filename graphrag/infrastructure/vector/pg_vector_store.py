"""
PostgresVectorStore — `IVectorStore`'un pgvector (PostgreSQL) uygulaması.

Vektörler pgvector sütununda saklanır; arama, veritabanının kendi kosinüs
mesafesi operatörüyle (`<=>`) yapılır. Benzerlik = 1 - kosinüs_mesafesi
(InMemoryVectorStore ile aynı anlam: yüksek skor = daha benzer).
"""
from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from graphrag.domain.entities import Chunk
from graphrag.domain.interfaces import IVectorStore
from graphrag.infrastructure.db.models import ChunkRow


class PostgresVectorStore(IVectorStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert(self, chunks: List[Chunk]) -> None:
        with Session(self._engine) as session:
            for chunk in chunks:
                document_id = chunk.chunk_id.split("#")[0]
                session.merge(ChunkRow(
                    chunk_id=chunk.chunk_id,
                    document_id=document_id,
                    text=chunk.text,
                    embedding=list(chunk.embedding),
                ))
            session.commit()

    def search(self, query_embedding: Tuple[float, ...], top_k: int):
        query = list(query_embedding)
        with Session(self._engine) as session:
            distance = ChunkRow.embedding.cosine_distance(query)
            stmt = (
                select(ChunkRow, distance.label("dist"))
                .order_by(distance)
                .limit(top_k)
            )
            rows = session.execute(stmt).all()
            return [
                (
                    Chunk(chunk_id=row.ChunkRow.chunk_id, text=row.ChunkRow.text,
                          embedding=tuple(row.ChunkRow.embedding)),
                    1.0 - row.dist,
                )
                for row in rows
            ]
