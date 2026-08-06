"""
API anahtarı doğrulaması için testler.

`API_KEY` ortam değişkeni ile davranış değişir:
  - tanımlı DEĞİLSE  → doğrulama kapalı (yerel geliştirme kolaylığı)
  - tanımlıysa       → veri uçları `X-API-Key` başlığı ister
Sağlık ucu (`/`) ve statik arayüz her hâlükârda açıktır.
"""
from fastapi.testclient import TestClient

from graphrag.api import app, get_core
from tests.test_api import _SahteCore

app.dependency_overrides[get_core] = lambda: _SahteCore()
client = TestClient(app)

ANAHTAR = "gizli-test-anahtari"


def test_anahtar_tanimsizken_dogrulama_kapali(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    assert client.get("/stats").status_code == 200
    assert client.get("/").json()["auth_enabled"] is False


def test_anahtar_tanimliyken_bassiz_istek_401(monkeypatch):
    monkeypatch.setenv("API_KEY", ANAHTAR)
    r = client.get("/stats")
    assert r.status_code == 401
    assert "API anahtarı" in r.json()["detail"]


def test_yanlis_anahtar_401(monkeypatch):
    monkeypatch.setenv("API_KEY", ANAHTAR)
    r = client.get("/stats", headers={"X-API-Key": "yanlis-anahtar"})
    assert r.status_code == 401


def test_dogru_anahtar_kabul_edilir(monkeypatch):
    monkeypatch.setenv("API_KEY", ANAHTAR)
    r = client.get("/stats", headers={"X-API-Key": ANAHTAR})
    assert r.status_code == 200
    assert r.json()["entities"] == 4


def test_saglik_ucu_anahtarsiz_erisilebilir(monkeypatch):
    # Durum göstergesi ve canlılık kontrolü anahtar istemez
    monkeypatch.setenv("API_KEY", ANAHTAR)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["auth_enabled"] is True


def test_web_arayuzu_anahtarsiz_servis_edilir(monkeypatch):
    # Statik HTML veri içermez; anahtar girişi arayüzün kendisinde yapılır
    monkeypatch.setenv("API_KEY", ANAHTAR)
    assert client.get("/app/").status_code == 200


def test_tum_veri_uclari_korunuyor(monkeypatch):
    """Hiçbir veri ucu yanlışlıkla korumasız kalmasın."""
    monkeypatch.setenv("API_KEY", ANAHTAR)
    korunmali = [
        ("get", "/stats"), ("get", "/documents"), ("get", "/entities"),
        ("get", "/audit"), ("get", "/connection?source=A&target=B"),
    ]
    for metot, yol in korunmali:
        assert getattr(client, metot)(yol).status_code == 401, f"{yol} korumasız!"

    assert client.post("/ask", json={"question": "x"}).status_code == 401
    assert client.post("/documents", json={"uri": "x.txt"}).status_code == 401
