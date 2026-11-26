"""
FastAPI endpoint'leri için testler.

Gerçek Ollama/veritabanı gerekmez: `get_core` bağımlılığını (Depends) SAHTE bir
çekirdekle değiştiririz (dependency override). Böylece HTTP katmanının doğru
çalıştığını (doğru metodu çağırıp doğru JSON'u döndürdüğünü) izole test ederiz.
"""
import pytest
import requests
from fastapi.testclient import TestClient

from graphrag import api
from graphrag.domain.entities import DocumentState
from graphrag.domain.exceptions import IngestionError

from graphrag.api import app, get_core


class _SahteDoc:
    document_id = "doc-1"
    state = DocumentState.PARSED    # gerçekteki gibi enum (upload `.value` okur)


class _SahteCore:
    """GraphRAGCore yerine geçen, sabit yanıt döndüren sahte çekirdek."""

    def __init__(self):
        self.silinenler = []

    def ingest(self, uri):
        return _SahteDoc()

    def delete_document(self, document_id):
        if document_id != "doc-1":
            return False
        self.silinenler.append(document_id)
        return True

    def clear_archive(self):
        self.silinenler.append("*")
        return 1

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
    r = client.post("/documents",
                    json={"uri": "ornek_belgeler/01_acme_danismanlik_sozlesmesi.txt"})
    assert r.status_code == 200
    assert r.json()["document_id"] == "doc-1"
    assert r.json()["state"] == "PARSED"


def test_documents_listesi_arsivdekileri_doner():
    r = client.get("/documents")
    assert r.status_code == 200
    assert any(d["name"] == "belge.txt" for d in r.json()["documents"])


def test_documents_silme_basarili_id_doner():
    r = client.delete("/documents/doc-1")
    assert r.status_code == 200
    assert r.json()["deleted"] == "doc-1"


def test_documents_silme_olmayan_belge_404_doner():
    r = client.delete("/documents/yok-boyle-bir-belge")
    assert r.status_code == 404


def test_documents_tumunu_silme_sayi_doner():
    r = client.delete("/documents")
    assert r.status_code == 200
    assert r.json()["deleted"] == 1


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


# --------------------------------------------------- girdi doğrulama ve hatalar

@pytest.fixture
def cekirdek(monkeypatch, tmp_path):
    """Teste özel sahte çekirdek; yüklemeler repo yerine geçici klasöre yazılır."""
    core = _SahteCore()
    core.yuklenenler = []
    core.ingest = lambda uri: (core.yuklenenler.append(uri), _SahteDoc())[1]
    monkeypatch.setitem(app.dependency_overrides, get_core, lambda: core)
    monkeypatch.setattr(api, "_UPLOAD_DIR", str(tmp_path))
    return core


@pytest.mark.parametrize("uri", ["README.md", "/etc/hosts",
                                 "ornek_belgeler/../graphrag/config.py"])
def test_documents_ornek_klasoru_disini_reddeder(cekirdek, uri):
    # Kısıt olmasaydı sunucudaki herhangi bir dosya arşive alınıp okunabilirdi.
    r = client.post("/documents", json={"uri": uri})
    assert r.status_code == 400
    assert cekirdek.yuklenenler == []


def test_upload_desteklenmeyen_uzantiyi_diske_yazmadan_reddeder(cekirdek, tmp_path):
    r = client.post("/upload", files=[("files", ("program.exe", b"MZ"))])
    assert r.status_code == 200
    assert r.json()["documents"] == []
    assert r.json()["errors"][0]["name"] == "program.exe"
    assert cekirdek.yuklenenler == []
    assert list(tmp_path.iterdir()) == []      # dosya hiç yazılmadı


def test_upload_ayni_adli_belgeyi_tekrar_yuklemez(cekirdek):
    # Sahte arşivde zaten "belge.txt" var.
    r = client.post("/upload", files=[("files", ("belge.txt", b"metin"))])
    assert r.json()["documents"] == []
    assert "zaten" in r.json()["errors"][0]["detail"]


def test_upload_kismi_basari_iki_listeyle_doner(cekirdek):
    r = client.post("/upload", files=[("files", ("yeni.txt", b"metin")),
                                      ("files", ("resim.png", b"png"))])
    body = r.json()
    assert [d["name"] for d in body["documents"]] == ["yeni.txt"]
    assert [e["name"] for e in body["errors"]] == ["resim.png"]


def test_upload_islenemeyen_dosyayi_siler_ve_nedenini_soyler(cekirdek, tmp_path):
    def patla(uri):
        raise IngestionError("Belgede okunabilir metin yok.")
    cekirdek.ingest = patla
    r = client.post("/upload", files=[("files", ("bos.txt", b" "))])
    assert r.json()["errors"][0]["detail"] == "Belgede okunabilir metin yok."
    assert list(tmp_path.iterdir()) == []      # yarım kalan dosya temizlendi


def test_ask_bos_soru_400_doner(cekirdek):
    r = client.post("/ask", json={"question": "   "})
    assert r.status_code == 400


def test_ingestion_hatasi_400_ve_mesajla_doner(cekirdek):
    def patla(uri):
        raise IngestionError("Desteklenmeyen dosya türü: .xyz")
    cekirdek.ingest = patla
    r = client.post("/documents",
                    json={"uri": "ornek_belgeler/01_acme_danismanlik_sozlesmesi.txt"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Desteklenmeyen dosya türü: .xyz"


def test_ollama_kapaliysa_503_ve_aciklama_doner(cekirdek):
    def patla(question):
        raise requests.ConnectionError("bağlantı reddedildi")
    cekirdek.answer_with_sources = patla
    r = client.post("/ask", json={"question": "merhaba"})
    assert r.status_code == 503
    assert "Ollama" in r.json()["detail"]
