"""
PostgreSQL kalıcılık adaptörleri için ENTEGRASYON testleri.

Bu testler gerçek bir Postgres (pgvector eklentili) gerektirir. Bu yüzden:
  - pgvector/psycopg kurulu değilse  -> modül atlanır (importorskip)
  - DATABASE_URL tanımlı değilse       -> testler atlanır (skipif)
Böylece normal `pytest` çalışması (veritabanısız) hiç etkilenmez.

Çalıştırmak için:
    docker compose up -d
    DATABASE_URL="postgresql+psycopg://graphrag:graphrag@localhost:5432/graphrag" \
        python3 -m pytest tests/test_persistence_postgres.py -v
"""
import os

import pytest

pytest.importorskip("pgvector")
pytest.importorskip("psycopg")

from sqlalchemy import select, text            # noqa: E402
from sqlalchemy.orm import Session             # noqa: E402

from graphrag.config import EMBED_DIM          # noqa: E402
from graphrag.domain.entities import Chunk, GraphEdge, GraphNode  # noqa: E402
from graphrag.domain.privacy import AuditEvent, PIIType           # noqa: E402
from graphrag.infrastructure.db.engine import init_schema, make_engine  # noqa: E402
from graphrag.infrastructure.db.models import AuditEventRow, Base       # noqa: E402
from graphrag.infrastructure.graph.pg_graph_store import PostgresGraphStore    # noqa: E402
from graphrag.infrastructure.privacy.pg_audit_log import PostgresAuditLog      # noqa: E402
from graphrag.infrastructure.vector.pg_vector_store import PostgresVectorStore  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tanımlı değil; Postgres entegrasyon testleri atlanıyor",
)


def _unit(i: int) -> tuple:
    """i'inci bileşeni 1, gerisi 0 olan EMBED_DIM boyutlu birim vektör."""
    vec = [0.0] * EMBED_DIM
    vec[i] = 1.0
    return tuple(vec)


@pytest.fixture
def pg_engine():
    engine = make_engine(DATABASE_URL)
    init_schema(engine)
    # Her testten önce tabloları temizle (izolasyon).
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))
    yield engine
    engine.dispose()


def test_pg_vector_store_benzerlik_sirasina_gore_dondurur(pg_engine):
    store = PostgresVectorStore(pg_engine)
    store.upsert([
        Chunk(chunk_id="d#0", text="birinci", embedding=_unit(0)),
        Chunk(chunk_id="d#1", text="ikinci", embedding=_unit(1)),
    ])

    sonuc = store.search(_unit(0), top_k=2)

    assert sonuc[0][0].text == "birinci"     # sorguya en yakın olan ilk sırada
    assert sonuc[0][1] > sonuc[1][1]         # skorlar azalan sırada


def test_pg_vector_store_upsert_gunceller(pg_engine):
    store = PostgresVectorStore(pg_engine)
    store.upsert([Chunk(chunk_id="d#0", text="eski", embedding=_unit(0))])
    store.upsert([Chunk(chunk_id="d#0", text="yeni", embedding=_unit(0))])  # aynı id

    sonuc = store.search(_unit(0), top_k=5)

    assert len(sonuc) == 1                    # çoğalmadı, güncellendi
    assert sonuc[0][0].text == "yeni"


def test_pg_graph_store_dugum_kenar_komsu(pg_engine):
    store = PostgresGraphStore(pg_engine)
    store.upsert_node(GraphNode(node_id="a", label="Acme"))
    store.upsert_node(GraphNode(node_id="b", label="Beta"))
    store.upsert_edge(GraphEdge("a", "b", 0.7, 0.5))

    komsular = store.neighbors("a")

    assert len(komsular) == 1
    assert komsular[0].target_id == "b"
    assert store.get_node("a").label == "Acme"


def test_pg_graph_store_olmayan_dugum_keyerror(pg_engine):
    store = PostgresGraphStore(pg_engine)
    with pytest.raises(KeyError):
        store.get_node("yok")


def test_pg_audit_log_olayi_kalici_kaydeder(pg_engine):
    log = PostgresAuditLog(pg_engine)
    log.record(AuditEvent(action="REDACT", pii_type=PIIType.TCKN,
                          placeholder="[TCKN_1]"))

    with Session(pg_engine) as session:
        rows = session.execute(select(AuditEventRow)).scalars().all()

    assert any(r.placeholder == "[TCKN_1]" and r.pii_type == "TCKN" for r in rows)
