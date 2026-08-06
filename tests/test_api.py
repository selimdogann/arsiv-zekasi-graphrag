"""
FastAPI endpoint'leri için testler.

Gerçek Ollama/veritabanı gerekmez: `get_core` bağımlılığını (Depends) SAHTE bir
çekirdekle değiştiririz (dependency override). Böylece HTTP katmanının doğru
çalıştığını (doğru metodu çağırıp doğru JSON'u döndürdüğünü) izole test ederiz.
"""
from fastapi.testclient import TestClient

from graphrag.api import app, get_core


class _SahteDoc:
    document_id = "doc-1"
    state = "PARSED"


class _SahteCore:
    """GraphRAGCore yerine geçen, sabit yanıt döndüren sahte çekirdek."""

    def ingest(self, uri):
        return _SahteDoc()

    def answer_with_sources(self, question):
        return {"answer": f"cevap: {question}",
                "sources": [{"chunk_id": "doc-1#0", "document_id": "doc-1",
                             "text": "kaynak metni"}]}

    def find_connection_detailed(self, source, target):
        return {"found": True, "nodes": [source, target],
                "relations": ["anlaştı"], "confidence": 0.5, "message": ""}

    def stats(self):
        return {"documents": 1, "chunks": 3, "entities": 4,
                "relations": 8, "pii_masked": 1}

    def documents(self):
        return [{"document_id": "doc-1", "name": "belge.txt",
                 "state": "PARSED", "uploaded_at": "2026-01-01T00:00:00"}]

    def entities(self):
        return ["Acme Holding", "Proje Zeus"]

    def audit_events(self):
        return [{"action": "REDACT", "pii_type": "TCKN",
                 "placeholder": "[TCKN_1]", "timestamp": "2026-01-01T00:00:00"}]


# get_core bağımlılığını sahte çekirdekle değiştir → gerçek Ollama'ya gidilmez.
app.dependency_overrides[get_core] = lambda: _SahteCore()
client = TestClient(app)


def test_health_servis_ve_depolama_durumu_doner():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "llm" in body and "storage" in body


def test_documents_ingest_cagirir():
    r = client.post("/documents", json={"uri": "herhangi/yol.txt"})
    assert r.status_code == 200
    assert r.json()["document_id"] == "doc-1"
    assert r.json()["state"] == "PARSED"


def test_documents_listesi_arsivdekileri_doner():
    r = client.get("/documents")
    assert r.status_code == 200
    assert any(d["name"] == "belge.txt" for d in r.json()["documents"])


def test_ask_cevabi_ve_kaynaklari_doner():
    r = client.post("/ask", json={"question": "merhaba"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "cevap: merhaba"
    assert body["sources"][0]["text"] == "kaynak metni"
    assert "document_name" in body["sources"][0]   # kaynak adı zenginleştirildi


def test_ask_eksik_alan_422_doner():
    # question alanı yoksa FastAPI/Pydantic otomatik doğrulama hatası (422) döner.
    r = client.post("/ask", json={})
    assert r.status_code == 422


def test_connection_yapilandirilmis_sonuc_doner():
    r = client.get("/connection", params={"source": "A", "target": "B"})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["nodes"] == ["A", "B"]
    assert body["relations"] == ["anlaştı"]


def test_stats_ozet_doner():
    r = client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["entities"] == 4
    assert "documents" in body


def test_entities_varlik_listesi_doner():
    r = client.get("/entities")
    assert r.status_code == 200
    assert "Proje Zeus" in r.json()["entities"]


def test_audit_kvkk_kaydini_doner():
    r = client.get("/audit")
    assert r.status_code == 200
    olay = r.json()["events"][0]
    assert olay["pii_type"] == "TCKN"
    assert olay["placeholder"] == "[TCKN_1]"


def test_web_arayuzu_sunuluyor():
    r = client.get("/app/")
    assert r.status_code == 200
    assert "Arşiv Zekâsı" in r.text
