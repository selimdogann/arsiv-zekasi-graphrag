"""
Composition Root — nesne grafının kurulduğu TEK yer.

Hangi somut sınıfın (PlainTextLoader, MockLanguageModel, ...) hangi porta
(IDocumentLoader, ILanguageModel, ...) takıldığı kararı SADECE burada verilir.
Uygulamanın geri kalanı bu kararları hiç görmez.
"""
from __future__ import annotations

from graphrag.application.graphrag_core import GraphRAGCore
from graphrag.infrastructure.graph.graph_store import InMemoryGraphStore
from graphrag.infrastructure.ingestion.document_loader import PlainTextLoader
from graphrag.infrastructure.llm.ollama_llm import OllamaLanguageModel
from graphrag.infrastructure.nlp.entity_extractor import SimpleEntityExtractor
from graphrag.infrastructure.privacy.audit_log import InMemoryAuditLog
from graphrag.infrastructure.privacy.kvkk_redactor import KvkkPiiRedactor
from graphrag.infrastructure.vector.vector_store import InMemoryVectorStore


def build_core() -> GraphRAGCore:
    audit_log = InMemoryAuditLog()
    return GraphRAGCore(
        loader=PlainTextLoader(),
        llm=OllamaLanguageModel(),
        vectors=InMemoryVectorStore(),
        graph=InMemoryGraphStore(),
        extractor=SimpleEntityExtractor(),
        privacy=KvkkPiiRedactor(audit_log),
    )
