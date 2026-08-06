"""
GraphRAGCore — uygulama katmanı (kullanım senaryolarını yöneten "orkestra şefi").

Bu sınıf HİÇBİR somut teknolojiyi bilmez — sadece `domain/interfaces.py`'deki
PORT'lara bağımlıdır (Dependency Injection).
"""
from __future__ import annotations
from graphrag.domain.text_tr import (
    canonical_entity_key,
    display_label,
    prefer_label,
    locate_in_source,
)

import math
from typing import List

from graphrag.domain.entities import (
    Chunk,
    Document,
    DocumentInfo,
    DocumentState,
    GraphEdge,
    GraphNode,
)
from graphrag.domain.exceptions import PathNotFoundError
from graphrag.application.fusion import reciprocal_rank_fusion
from graphrag.domain.interfaces import (
    IAuditLog,
    IChunker,
    IDocumentCatalog,
    IDocumentLoader,
    IEntityExtractor,
    IGraphStore,
    IKeywordIndex,
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
                 chunker: IChunker, keyword_index: IKeywordIndex,
                 audit_log: IAuditLog, catalog: IDocumentCatalog) -> None:
        self._loader = loader
        self._llm = llm
        self._vectors = vectors
        self._graph = graph
        self._search = GraphSearchEngine(graph)
        self._extractor = extractor
        self._privacy = privacy
        self._chunker = chunker
        self._keyword = keyword_index
        self._audit = audit_log
        self._catalog = catalog

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
        self._keyword.index(chunks)   # aynı parçaları anahtar-kelime (BM25) indeksine de koy

        entity_names = self._extractor.extract(document.raw_text)
        node_ids = []
        for name in entity_names:
            # TEMELLENDİRME: belgede geçmeyen ad, LLM'in uydurmasıdır —
            # grafa alınmaz. Bulunursa belgedeki yazım kullanılır (İ/ı
            # bozulmasını da önler).
            kaynak_yazim = locate_in_source(name, document.raw_text)
            if kaynak_yazim is None:
                continue
            # Şirket eki temizlenmiş kimlik: "ACME HOLDİNG A.Ş." ile
            # "Acme Holding" tek düğümde birleşir.
            node_id = canonical_entity_key(kaynak_yazim)
            label = display_label(kaynak_yazim)
            try:
                # Aynı varlık daha önce görüldüyse, gösterime uygun etiketi koru.
                label = prefer_label(self._graph.get_node(node_id).label, label)
            except KeyError:
                pass
            self._graph.upsert_node(GraphNode(node_id=node_id, label=label))
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

        # Belge kaydı: adı ve durumu kalıcı olarak sakla — böylece sunucu
        # yeniden başlasa da liste ve kaynak gösterimindeki ad korunur.
        self._catalog.add(DocumentInfo(
            document_id=document.document_id,
            name=uri.rsplit("/", 1)[-1],      # yalnızca dosya adı
            state=document.state.value,
            created_at=document.created_at.isoformat(timespec="seconds"),
        ))
        return document

    def answer(self, question: str) -> str:
        """Soruyu yanıtlar (yalnızca cevap metni)."""
        return self.answer_with_sources(question)["answer"]

    def answer_with_sources(self, question: str) -> dict:
        """Soruyu yanıtlar VE cevabın dayandığı kaynak parçaları döndürür.

        Kurumsal/hukuki kullanımda "bu bilgi nereden geldi?" sorusu kritiktir:
        kaynak gösterimi (citation), cevabın doğrulanabilir olmasını sağlar.
        """
        # MELEZ (hybrid) retrieval: anlamsal (vektör) + anahtar kelime (BM25)
        # aramalarını ayrı ayrı yapıp, sonuçları RRF ile birleştir.
        question_embedding = self._llm.embed(question)
        vector_hits = self._vectors.search(question_embedding, top_k=10)
        keyword_hits = self._keyword.search(question, top_k=10)

        by_id = {chunk.chunk_id: chunk for chunk, _ in vector_hits}
        by_id.update({chunk.chunk_id: chunk for chunk, _ in keyword_hits})
        if not by_id:
            return {"answer": "Arşivde bu soruyla ilgili bir şey bulamadım.",
                    "sources": []}

        vector_ranking = [chunk.chunk_id for chunk, _ in vector_hits]
        keyword_ranking = [chunk.chunk_id for chunk, _ in keyword_hits]
        fused_ids = reciprocal_rank_fusion([vector_ranking, keyword_ranking])[:3]

        # Birleşik sıralamada en iyi parçaları tek bir BAĞLAM'a çevir.
        context = "\n\n".join(by_id[chunk_id].text for chunk_id in fused_ids)
        prompt = (
    "Aşağıdaki BAĞLAM'a dayanarak soruyu yanıtla. SADECE bağlamda verilen "
    "bilgiyi kullan; bağlamda olmayan hiçbir şeyi UYDURMA. Bağlamda cevap "
    "yoksa 'Bu bilgi arşivde bulunamadı' de.\n\n"
    f"BAĞLAM: {context}\n\n"
    f"SORU: {question}\n\n"
    "CEVAP:"
)

        sources = [
            {"chunk_id": cid,
             "document_id": cid.split("#")[0],
             "text": by_id[cid].text}
            for cid in fused_ids
        ]
        return {"answer": self._llm.complete(prompt), "sources": sources}

    # ---------------------------------------------------------------- sorgular

    def stats(self) -> dict:
        """Arşivin özet istatistikleri (gösterge paneli için)."""
        return {
            "documents": len(self._catalog.all()),
            "chunks": self._vectors.count(),
            "entities": len(self._graph.all_nodes()),
            "relations": self._graph.edge_count(),
            "pii_masked": len(self._audit.events()),
        }

    def documents(self) -> List[dict]:
        """Arşivdeki belgeler (en yeniden eskiye)."""
        return [
            {"document_id": d.document_id, "name": d.name,
             "state": d.state, "uploaded_at": d.created_at}
            for d in self._catalog.all()
        ]

    def entities(self) -> List[str]:
        """Graftaki tüm varlıkların okunabilir adları (alfabetik)."""
        return sorted(node.label for node in self._graph.all_nodes())

    def audit_events(self) -> List[dict]:
        """KVKK denetim kayıtları (en yeniden eskiye)."""
        return [
            {"action": e.action, "pii_type": e.pii_type.value,
             "placeholder": e.placeholder, "timestamp": e.timestamp}
            for e in reversed(self._audit.events())
        ]

    def find_connection(self, source_id: str, target_id: str) -> str:
        # Girdi de aynı kurallarla normalize edilir: kullanıcı "Acme Holding A.Ş."
        # yazsa bile "Acme Holding" düğümüne ulaşır.
        source_key = canonical_entity_key(source_id)
        target_key = canonical_entity_key(target_id)
        try:
            path = self._search.shortest_path(source_key, target_key)
        except PathNotFoundError:
            return "Bu iki varlık arasında bilinen bir bağlantı bulunamadı."

        labels = [self._graph.get_node(nid).label for nid in path.nodes]
        chain = " -> ".join(labels)
        return f"Bağlantı bulundu: {chain}  (güven: {path.probability:.2f})"
