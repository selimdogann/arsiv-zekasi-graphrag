"""
Composition Root — nesne grafının kurulduğu TEK yer.

Hangi somut sınıfın (PlainTextLoader, OllamaLanguageModel, ...) hangi porta
(IDocumentLoader, ILanguageModel, ...) takıldığı kararı SADECE burada verilir.
Uygulamanın geri kalanı bu kararları hiç görmez.

Kalıcılık seçimi de burada yapılır: `DATABASE_URL` ortam değişkeni tanımlıysa
PostgreSQL adaptörleri, tanımlı değilse bellek-içi (InMemory) adaptörler
kullanılır. GraphRAGCore bu seçimden habersizdir — sadece porta bakar.
"""
from __future__ import annotations

from graphrag.application.graphrag_core import GraphRAGCore
from graphrag.config import get_settings
from graphrag.infrastructure.cache.memory_cache import InMemoryCache
from graphrag.infrastructure.chunking.text_chunker import SlidingWindowChunker
from graphrag.infrastructure.graph.graph_store import InMemoryGraphStore
from graphrag.infrastructure.ingestion.auto_loader import AutoDocumentLoader
from graphrag.infrastructure.keyword.bm25_index import InMemoryKeywordIndex
from graphrag.infrastructure.llm.cached_llm import CachedLanguageModel
from graphrag.infrastructure.llm.ollama_llm import OllamaLanguageModel
from graphrag.infrastructure.nlp.entity_filter import FilteredEntityExtractor
from graphrag.infrastructure.nlp.llm_entity_extractor import LlmEntityExtractor
from graphrag.infrastructure.privacy.audit_log import InMemoryAuditLog
from graphrag.infrastructure.privacy.kvkk_redactor import KvkkPiiRedactor
from graphrag.infrastructure.vector.vector_store import InMemoryVectorStore


def _build_storage():
    """DATABASE_URL varsa kalıcı Postgres, yoksa bellek-içi depoları döndürür.

    Postgres importları bilerek fonksiyon İÇİNDE (lazy) yapılır: bir veritabanı
    kütüphanesi kurulu olmasa bile bellek-içi mod sorunsuz çalışsın diye.
    """
    settings = get_settings()
    if settings.database_url:
        from graphrag.infrastructure.db.engine import init_schema, make_engine
        from graphrag.infrastructure.graph.pg_graph_store import PostgresGraphStore
        from graphrag.infrastructure.privacy.pg_audit_log import PostgresAuditLog
        from graphrag.infrastructure.vector.pg_vector_store import PostgresVectorStore

        engine = make_engine(settings.database_url)
        init_schema(engine)
        return (
            PostgresAuditLog(engine),
            PostgresVectorStore(engine),
            PostgresGraphStore(engine),
        )
    return (InMemoryAuditLog(), InMemoryVectorStore(), InMemoryGraphStore())


def build_core() -> GraphRAGCore:
    audit_log, vectors, graph = _build_storage()
    # Tek bir önbellekli LLM; hem cevap üretimi hem varlık çıkarımı paylaşır.
    llm = CachedLanguageModel(OllamaLanguageModel(), InMemoryCache())

    # BM25 indeksi bellek-içidir; kalıcı depoda zaten duran parçalarla açılışta
    # yeniden kurulur. Aksi hâlde sunucu yeniden başladığında melez arama tek
    # ayak (yalnızca anlamsal) kalır ve tam terim aramaları zayıflar.
    keyword_index = InMemoryKeywordIndex()
    existing = vectors.all_chunks()
    if existing:
        keyword_index.index(existing)

    return GraphRAGCore(
        loader=AutoDocumentLoader(),
        llm=llm,
        vectors=vectors,
        graph=graph,
        # LLM çıkarımı süzgeçten geçer: IBAN/TCKN/adres/kod/başlık gibi
        # adaylar grafa varlık olarak girmez.
        extractor=FilteredEntityExtractor(LlmEntityExtractor(llm)),
        privacy=KvkkPiiRedactor(audit_log),
        chunker=SlidingWindowChunker(),
        keyword_index=keyword_index,
        audit_log=audit_log,
    )
