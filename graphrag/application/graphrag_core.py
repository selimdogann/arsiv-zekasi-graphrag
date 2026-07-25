"""
GraphRAGCore — uygulama katmanı (kullanım senaryolarını yöneten "orkestra şefi").

Bu sınıf HİÇBİR somut teknolojiyi bilmez — sadece `domain/interfaces.py`'deki
PORT'lara bağımlıdır (Dependency Injection).
"""
from __future__ import annotations

import math

from graphrag.domain.entities import Chunk, Document, DocumentState, GraphEdge, GraphNode
from graphrag.domain.exceptions import PathNotFoundError
from graphrag.domain.interfaces import (
    IDocumentLoader,
    IEntityExtractor,
    IGraphStore,
    ILanguageModel,
    IVectorStore,
)
from graphrag.infrastructure.graph.graph_search_engine import GraphSearchEngine

_CO_OCCURRENCE_CONFIDENCE = 0.5


class GraphRAGCore:
    def __init__(self, loader: IDocumentLoader, llm: ILanguageModel,
                 vectors: IVectorStore, graph: IGraphStore,
                 extractor: IEntityExtractor) -> None:
        self._loader = loader
        self._llm = llm
        self._vectors = vectors
        self._graph = graph
        self._search = GraphSearchEngine(graph)
        self._extractor = extractor

    def ingest(self, uri: str) -> Document:
        document = self._loader.load(uri)
        document.transition_to(DocumentState.PARSING, note="ingest başladı")

        embedding = self._llm.embed(document.raw_text)
        chunk = Chunk(chunk_id=document.document_id, text=document.raw_text,
                      embedding=embedding)
        self._vectors.upsert([chunk])

        entity_names = self._extractor.extract(document.raw_text)
        for name in entity_names:
            self._graph.upsert_node(GraphNode(node_id=name, label=name))

        weight = -math.log(_CO_OCCURRENCE_CONFIDENCE)
        for i in range(len(entity_names)):
            for j in range(i + 1, len(entity_names)):
                a, b = entity_names[i], entity_names[j]
                self._graph.upsert_edge(
                    GraphEdge(a, b, weight, _CO_OCCURRENCE_CONFIDENCE))
                self._graph.upsert_edge(
                    GraphEdge(b, a, weight, _CO_OCCURRENCE_CONFIDENCE))

        document.transition_to(
            DocumentState.PARSED,
            note=f"metin hazır, {len(entity_names)} varlık çıkarıldı")
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
        try:
            path = self._search.shortest_path(source_id, target_id)
        except PathNotFoundError:
            return "Bu iki varlık arasında bilinen bir bağlantı bulunamadı."

        chain = " -> ".join(path.nodes)
        return f"Bağlantı bulundu: {chain}  (güven: {path.probability:.2f})"
