"""
GraphRAGCore — uygulama katmanı (kullanım senaryolarını yöneten "orkestra şefi").

Bu sınıf HİÇBİR somut teknolojiyi bilmez — sadece `domain/interfaces.py`'deki
PORT'lara bağımlıdır (Dependency Injection).
"""
from __future__ import annotations

from graphrag.domain.entities import Chunk, Document, DocumentState
from graphrag.domain.exceptions import PathNotFoundError
from graphrag.domain.interfaces import (
    IDocumentLoader,
    IGraphStore,
    ILanguageModel,
    IVectorStore,
)
from graphrag.infrastructure.graph.graph_search_engine import GraphSearchEngine


class GraphRAGCore:
    def __init__(self, loader: IDocumentLoader, llm: ILanguageModel,
                 vectors: IVectorStore, graph: IGraphStore) -> None:
        self._loader = loader
        self._llm = llm
        self._vectors = vectors
        self._graph = graph
        self._search = GraphSearchEngine(graph)

    def ingest(self, uri: str) -> Document:
        document = self._loader.load(uri)
        document.transition_to(DocumentState.PARSING, note="ingest başladı")

        embedding = self._llm.embed(document.raw_text)
        chunk = Chunk(chunk_id=document.document_id, text=document.raw_text,
                      embedding=embedding)
        self._vectors.upsert([chunk])

        document.transition_to(DocumentState.PARSED, note="metin hazır ve indekslendi")
        return document

    def answer(self, question: str) -> str:
        question_embedding = self._llm.embed(question)
        results = self._vectors.search(question_embedding, top_k=1)
        if not results:
            return "Arşivde bu soruyla ilgili bir şey bulamadım."

        best_chunk, score = results[0]
        prompt = f"Bağlam: {best_chunk.text}\n\nSoru: {question}\n\nCevap:"
        return self._llm.complete(prompt)

    def find_connection(self, source_id: str, target_id: str) -> str:
        """İki varlık arasında, graf üzerinden en güvenilir bağlantı zincirini bulur."""
        try:
            path = self._search.shortest_path(source_id, target_id)
        except PathNotFoundError:
            return "Bu iki varlık arasında bilinen bir bağlantı bulunamadı."

        chain = " -> ".join(path.nodes)
        return f"Bağlantı bulundu: {chain}  (güven: {path.probability:.2f})"
