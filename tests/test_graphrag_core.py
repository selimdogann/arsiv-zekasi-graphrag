"""
GraphRAGCore (uygulama katmanı / "orkestra şefi") için ENTEGRASYON testleri.

Buradaki fikir, mimarinin en güzel meyvesidir: GraphRAGCore yalnızca
SÖZLEŞMELERE bağımlı olduğundan, gerçek bir LLM'e (Ollama) hiç ihtiyaç
duymadan tüm akışı test edebiliriz. Deterministik olan gerçek bileşenleri
(vektör deposu, graf, varlık çıkarıcı, KVKK maskeleyici, chunker) OLDUĞU GİBİ
kullanır; yalnızca dış dünyaya (ağ/dosya) bağımlı iki parçayı SAHTELERİYLE
(test double) değiştiririz:
  - `_SahteLoader`: dosya yerine bellekten metin verir.
  - `_KaydedenSahteLLM`: ağ yerine sabit yanıt döner ve KENDİSİNE verilen
    prompt'u kaydeder (böylece RAG'ın doğru bağlamı geçirdiğini kanıtlarız).
"""
import hashlib

from graphrag.application.graphrag_core import GraphRAGCore
from graphrag.domain.entities import Document, DocumentState
from graphrag.domain.interfaces import IDocumentLoader, ILanguageModel
from graphrag.domain.text_tr import canonical_key
from graphrag.infrastructure.catalog.memory_catalog import InMemoryDocumentCatalog
from graphrag.infrastructure.chunking.text_chunker import SlidingWindowChunker
from graphrag.infrastructure.graph.graph_store import InMemoryGraphStore
from graphrag.infrastructure.keyword.bm25_index import InMemoryKeywordIndex
from graphrag.infrastructure.nlp.entity_extractor import SimpleEntityExtractor
from graphrag.infrastructure.privacy.audit_log import InMemoryAuditLog
from graphrag.infrastructure.privacy.kvkk_redactor import KvkkPiiRedactor
from graphrag.infrastructure.vector.vector_store import InMemoryVectorStore


class _SahteLoader(IDocumentLoader):
    """Dosya yerine, bellekteki bir sözlükten metin döndüren sahte yükleyici."""

    def __init__(self) -> None:
        self.texts = {}

    def load(self, uri: str) -> Document:
        return Document(uri=uri, title=uri, raw_text=self.texts[uri])


class _KaydedenSahteLLM(ILanguageModel):
    """Sabit yanıt döner; kendisine verilen son prompt'u kaydeder."""

    def __init__(self) -> None:
        self.last_prompt = None

    def complete(self, prompt: str) -> str:
        self.last_prompt = prompt
        return "sahte cevap"

    def embed(self, text: str):
        # Deterministik: aynı metin -> aynı vektör (semantik anlam taşımaz,
        # sadece akışı test etmek için yeterli).
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return (float(h % 1000), float((h // 1000) % 1000), 1.0)


def _core_kur():
    """Gerçek deterministik bileşenler + sahte loader/LLM ile bir core kurar."""
    loader = _SahteLoader()
    llm = _KaydedenSahteLLM()
    vectors = InMemoryVectorStore()
    graph = InMemoryGraphStore()
    audit_log = InMemoryAuditLog()
    core = GraphRAGCore(
        loader=loader,
        llm=llm,
        vectors=vectors,
        graph=graph,
        extractor=SimpleEntityExtractor(),
        privacy=KvkkPiiRedactor(audit_log),
        chunker=SlidingWindowChunker(),
        keyword_index=InMemoryKeywordIndex(),
        audit_log=audit_log,
        catalog=InMemoryDocumentCatalog(),
    )
    return core, loader, llm, vectors, graph


# ---------------------------------------------------------------- ingest

def test_ingest_belgeyi_parsed_durumuna_getirir():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["a"] = "Basit bir metin."
    doc = core.ingest("a")
    assert doc.state == DocumentState.PARSED


def test_ingest_parcalari_vektor_deposuna_yazar():
    core, loader, llm, vectors, _graph = _core_kur()
    loader.texts["a"] = "kelime " * 300   # uzun metin -> birden fazla parça
    core.ingest("a")
    sonuclar = vectors.search(llm.embed("kelime"), top_k=10)
    assert len(sonuclar) >= 2


def test_ingest_varliklari_grafa_ekler():
    core, loader, _llm, _vec, graph = _core_kur()
    loader.texts["a"] = "Acme Holding, Proje Zeus için Beta Firması ile anlaştı."
    core.ingest("a")
    dugum = graph.get_node(canonical_key("Acme Holding"))
    assert dugum.label == "Acme Holding"


def test_ingest_pii_maskeler_ham_tckn_depoya_girmez():
    core, loader, llm, vectors, _graph = _core_kur()
    loader.texts["gizli"] = "Müşteri TCKN 10000000146 olarak kayıtlıdır."
    core.ingest("gizli")
    sonuclar = vectors.search(llm.embed("TCKN"), top_k=5)
    depodaki_metin = " ".join(chunk.text for chunk, _ in sonuclar)
    assert "10000000146" not in depodaki_metin   # ham TCKN sızmamalı
    assert "[TCKN_1]" in depodaki_metin           # yerine placeholder olmalı


# ---------------------------------------------------------------- answer

def test_answer_baglami_ve_soruyu_llme_gecirir():
    core, loader, llm, _vec, _graph = _core_kur()
    loader.texts["a"] = "Proje Zeus, Acme Holding tarafından yürütülmektedir."
    core.ingest("a")
    core.answer("Proje Zeus kimin?")
    assert "Proje Zeus" in llm.last_prompt          # bağlam prompt'a girmiş
    assert "Proje Zeus kimin?" in llm.last_prompt    # soru da prompt'a girmiş


def test_answer_bos_arsivde_bulamadigini_soyler():
    core, _loader, _llm, _vec, _graph = _core_kur()
    cevap = core.answer("herhangi bir soru")
    assert "bulamadım" in cevap.lower()


# ---------------------------------------------------------------- find_connection

def test_find_connection_ortak_varlik_uzerinden_baglar():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["a"] = "Acme Holding, Proje Zeus için Beta Firması ile anlaştı."
    loader.texts["b"] = "Proje Zeus kapsamında Gamma Danışmanlık teknik destek verdi."
    core.ingest("a")
    core.ingest("b")
    sonuc = core.find_connection("Acme Holding", "Gamma Danışmanlık")
    assert "Proje Zeus" in sonuc
    assert "bulunamadı" not in sonuc


def test_find_connection_baglanti_yoksa_bilgilendirir():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["a"] = "Acme Holding, Proje Zeus için Beta Firması ile anlaştı."
    core.ingest("a")
    sonuc = core.find_connection("Acme Holding", "Gamma Danışmanlık")
    assert "bulunamadı" in sonuc


# ---------------------------------------------------------- sorgu/rapor API'si

def test_answer_with_sources_kaynak_dondurur():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["a"] = "Proje Zeus, Acme Holding tarafından yürütülmektedir."
    doc = core.ingest("a")

    sonuc = core.answer_with_sources("Proje Zeus nedir?")

    assert sonuc["sources"], "cevap en az bir kaynağa dayanmalı"
    assert sonuc["sources"][0]["document_id"] == doc.document_id
    assert "Proje Zeus" in sonuc["sources"][0]["text"]


def test_stats_arsiv_ozetini_verir():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["a"] = "Acme Holding, Proje Zeus için Beta Firması ile anlaştı."
    core.ingest("a")

    s = core.stats()

    assert s["chunks"] >= 1
    assert s["entities"] >= 3       # Acme Holding, Proje Zeus, Beta Firması
    assert s["relations"] >= 6      # 3 varlık -> 3 çift -> çift yönlü 6 kenar


def test_entities_varlik_adlarini_alfabetik_verir():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["a"] = "Acme Holding, Proje Zeus için Beta Firması ile anlaştı."
    core.ingest("a")

    isimler = core.entities()

    assert "Acme Holding" in isimler
    assert isimler == sorted(isimler)


def test_audit_events_maskelemeyi_raporlar():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["gizli"] = "Müşteri TCKN 10000000146 olarak kayıtlıdır."
    core.ingest("gizli")

    olaylar = core.audit_events()

    assert olaylar, "maskeleme denetim kaydına yazılmalı"
    assert olaylar[0]["pii_type"] == "TCKN"
    assert olaylar[0]["placeholder"] == "[TCKN_1]"
    # Veri minimizasyonu: ham TCKN denetim kaydında ASLA görünmemeli
    assert all("10000000146" not in str(o) for o in olaylar)


# ------------------------------------------------------- belge kaydı (katalog)

def test_ingest_belgeyi_kataloga_kaydeder():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["klasor/sozlesme.txt"] = "Acme Holding ile anlaşma yapıldı."
    doc = core.ingest("klasor/sozlesme.txt")

    kayitlar = core.documents()

    assert len(kayitlar) == 1
    assert kayitlar[0]["document_id"] == doc.document_id
    assert kayitlar[0]["name"] == "sozlesme.txt"     # yalnızca dosya adı
    assert kayitlar[0]["state"] == "PARSED"


def test_stats_belge_sayisini_katalogdan_alir():
    core, loader, _llm, _vec, _graph = _core_kur()
    loader.texts["a.txt"] = "Acme Holding."
    loader.texts["b.txt"] = "Delta Lojistik."
    core.ingest("a.txt"); core.ingest("b.txt")

    assert core.stats()["documents"] == 2
