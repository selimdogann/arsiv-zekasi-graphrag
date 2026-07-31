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

    def answer(self, question):
        return f"cevap: {question}"

    def find_connection(self, source, target):
        return f"{source} -> {target}"


# get_core bağımlılığını sahte çekirdekle değiştir → gerçek Ollama'ya gidilmez.
app.dependency_overrides[get_core] = lambda: _SahteCore()
client = TestClient(app)


def test_health_ok_doner():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_documents_ingest_cagirir():
    r = client.post("/documents", json={"uri": "herhangi/yol.txt"})
    assert r.status_code == 200
    assert r.json() == {"document_id": "doc-1", "state": "PARSED"}


def test_ask_soruyu_cekirdege_gecirir():
    r = client.post("/ask", json={"question": "merhaba"})
    assert r.status_code == 200
    assert r.json() == {"answer": "cevap: merhaba"}


def test_ask_eksik_alan_422_doner():
    # question alanı yoksa FastAPI/Pydantic otomatik doğrulama hatası (422) döner.
    r = client.post("/ask", json={})
    assert r.status_code == 422


def test_connection_kaynak_ve_hedefi_gecirir():
    r = client.get("/connection", params={"source": "A", "target": "B"})
    assert r.status_code == 200
    assert r.json() == {"result": "A -> B"}


def test_web_arayuzu_sunuluyor():
    # /app/ statik arayüz sayfasını (HTML) döndürmeli.
    r = client.get("/app/")
    assert r.status_code == 200
    assert "Arşiv Zekâsı" in r.text
