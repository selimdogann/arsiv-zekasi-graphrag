"""
GraphRAGCore — uygulama katmanı (kullanım senaryolarını yöneten "orkestra şefi").

Bu sınıf HİÇBİR somut teknolojiyi bilmez — sadece `domain/interfaces.py`'deki
PORT'lara bağımlıdır (Dependency Injection).
"""
from __future__ import annotations
from graphrag.domain.text_tr import canonical_key

import math

from graphrag.domain.entities import Chunk, Document, DocumentState, GraphEdge, GraphNode
from graphrag.domain.exceptions import PathNotFoundError
from graphrag.domain.interfaces import (
    IChunker,
    IDocumentLoader,
    IEntityExtractor,
    IGraphStore,
    ILanguageModel,
    IPrivacyFilter,
    IVectorStore,
)
from graphrag.infrastructure.graph.graph_search_engine import GraphSearchEngine

_CO_OCCURRENCE_CONFIDENCE = 0.5


class GraphRAGCore:
    def __init__(self, loader: IDocumentLoader, llm: ILanguageModel,
                 vectors: IVectorStore, graph: IGraphStore,
                 extractor: IEntityExtractor, privacy: IPrivacyFilter,
                 chunker: IChunker) -> None:
        self._loader = loader
        self._llm = llm
        self._vectors = vectors
        self._graph = graph
        self._search = GraphSearchEngine(graph)
        self._extractor = extractor
        self._privacy = privacy
        self._chunker = chunker

    def ingest(self, uri: str) -> Document:
        document = self._loader.load(uri)
        document.transition_to(DocumentState.PARSING, note="ingest başladı")

        # KVKK: kişisel veriler, embed/graf-çıkarım öncesi maskelenir — böylece
        # ham kişisel veri hiçbir zaman vektör deposuna ya da grafa girmez.
        document.raw_text = self._privacy.redact(document.raw_text)

        # Belgeyi küçük parçalara böl ve HER parçayı ayrı ayrı embed'le.
        # Böylece arama, koca belgeyi değil, sorunun geçtiği asıl parçayı bulur.
        pieces = self._chunker.chunk(document.raw_text)
        chunks = [
            Chunk(chunk_id=f"{document.document_id}#{i}", text=piece,
                  embedding=self._llm.embed(piece))
            for i, piece in enumerate(pieces)
        ]
        self._vectors.upsert(chunks)

        entity_names = self._extractor.extract(document.raw_text)
        node_ids = []
        for name in entity_names:
            node_id = canonical_key(name)
            self._graph.upsert_node(GraphNode(node_id=node_id, label=name))
            node_ids.append(node_id)

        weight = -math.log(_CO_OCCURRENCE_CONFIDENCE)
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                a, b = node_ids[i], node_ids[j]
                if a == b:
                    continue  # aynı varlığın farklı yazımı, zaten aynı düğüm
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
        results = self._vectors.search(question_embedding, top_k=3)
        if not results:
            return "Arşivde bu soruyla ilgili bir şey bulamadım."

        # En benzer birkaç parçayı birleştirip tek bir BAĞLAM oluştur.
        context = "\n\n".join(chunk.text for chunk, score in results)
        prompt = (
    "Aşağıdaki BAĞLAM'a dayanarak soruyu yanıtla. SADECE bağlamda verilen "
    "bilgiyi kullan; bağlamda olmayan hiçbir şeyi UYDURMA. Bağlamda cevap "
    "yoksa 'Bu bilgi arşivde bulunamadı' de.\n\n"
    f"BAĞLAM: {context}\n\n"
    f"SORU: {question}\n\n"
    "CEVAP:"
)

        return self._llm.complete(prompt)

    def find_connection(self, source_id: str, target_id: str) -> str:
        source_key = canonical_key(source_id)
        target_key = canonical_key(target_id)
        try:
            path = self._search.shortest_path(source_key, target_key)
        except PathNotFoundError:
            return "Bu iki varlık arasında bilinen bir bağlantı bulunamadı."

        labels = [self._graph.get_node(nid).label for nid in path.nodes]
        chain = " -> ".join(labels)
        return f"Bağlantı bulundu: {chain}  (güven: {path.probability:.2f})"
