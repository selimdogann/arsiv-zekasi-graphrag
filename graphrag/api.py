"""
FastAPI web servisi — GraphRAGCore'u HTTP üzerinden dışa açar.

Bu dosya, projeyi "çalışan bir servise" çevirir: `demo.py` çekirdeği terminalden
sürüyordu; bu API aynı çekirdeği HTTP'den sunar. GraphRAGCore burada da
değişmez — bu dosya sadece yeni bir "giriş kapısı".

Çekirdek, `get_core` bağımlılığı (Depends) üzerinden verilir. Böylece testlerde
gerçek Ollama'ya gitmeden, sahte bir çekirdekle değiştirilebilir.

Çalıştırma:
    uvicorn graphrag.api:app --reload
Sonra tarayıcıda: http://localhost:8000/app/
"""
from __future__ import annotations

import os
import secrets
from typing import List, Optional

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graphrag.application.graphrag_core import GraphRAGCore
from graphrag.composition import build_core
from graphrag.config import get_settings
from graphrag.infrastructure.llm.ollama_llm import CHAT_MODEL, EMBED_MODEL

OLLAMA_BASE = "http://localhost:11434"

app = FastAPI(title="Arşiv Zekâsı API", version="1.0.0")

# Çekirdek İLK istekte bir kez kurulur (lazy singleton) ve tüm istekler paylaşır.
_core: "GraphRAGCore | None" = None

def get_core() -> GraphRAGCore:
    """Endpoint'lere çekirdeği veren bağımlılık. Testte override edilebilir."""
    global _core
    if _core is None:
        _core = build_core()
    return _core


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Veri uçlarını API anahtarıyla korur (`X-API-Key` başlığı).

    `API_KEY` ortam değişkeni tanımlı DEĞİLSE doğrulama kapalıdır; bu, yerel
    geliştirmeyi kolaylaştırır ve sağlık ucunda `auth_enabled: false` olarak
    açıkça bildirilir. On-premise kurulumda `API_KEY` mutlaka verilmelidir.

    Karşılaştırma `secrets.compare_digest` ile yapılır: anahtarı karakter
    karakter tahmin etmeye yarayan zamanlama (timing) saldırısını önler.
    """
    beklenen = get_settings().api_key
    if beklenen is None:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, beklenen):
        raise HTTPException(
            status_code=401,
            detail="Geçersiz veya eksik API anahtarı (X-API-Key başlığı).",
        )


# Korunan uçlarda ortak kullanılan bağımlılık listesi
_KORUMALI = [Depends(require_api_key)]


# --- İstek gövdelerinin (JSON) şekli: Pydantic modelleri ---------------------

class IngestRequest(BaseModel):
    uri: str            # yüklenecek belgenin sunucudaki yolu


class AskRequest(BaseModel):
    question: str


# --- Sistem durumu -----------------------------------------------------------

_health_engine = None


def _database_up(database_url: str) -> bool:
    """Veritabanına gerçekten bağlanılabiliyor mu? (basit SELECT 1 yoklaması)"""
    global _health_engine
    try:
        from sqlalchemy import text

        from graphrag.infrastructure.db.engine import make_engine
        if _health_engine is None:
            _health_engine = make_engine(database_url)
        with _health_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@app.get("/")
def health():
    """Servis ve bağımlılıklarının GERÇEK durumu (arayüzdeki canlı göstergeler)."""
    try:
        requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
        llm_up = True
    except Exception:
        llm_up = False

    database_url = get_settings().database_url
    return {
        "status": "ok",
        "llm": llm_up,
        "storage": "PostgreSQL" if database_url else "Bellek-içi",
        "persistent": bool(database_url),
        # Gerçek bağlantı yoklaması: DATABASE_URL tanımlı olsa bile veritabanı
        # kapalıysa `false` döner (gösterge sahte yeşil yanmasın).
        "database": _database_up(database_url) if database_url else False,
        "chat_model": CHAT_MODEL,
        "embed_model": EMBED_MODEL,
        # Doğrulama kapalıysa arayüz ve yönetici bunu açıkça görebilsin
        "auth_enabled": get_settings().api_key is not None,
    }


@app.get("/stats", dependencies=_KORUMALI)
def stats(core: GraphRAGCore = Depends(get_core)):
    """Arşiv özeti: parça, varlık, ilişki ve maskelenen kişisel veri sayısı."""
    return core.stats()


# --- Belgeler ----------------------------------------------------------------

@app.get("/documents", dependencies=_KORUMALI)
def list_documents(core: GraphRAGCore = Depends(get_core)):
    """Arşivdeki belgelerin listesi (kalıcı)."""
    return {"documents": core.documents()}


@app.post("/documents", dependencies=_KORUMALI)
def ingest_document(req: IngestRequest, core: GraphRAGCore = Depends(get_core)):
    """Sunucudaki bir belge yolunu ingest eder (örnek belgeler için)."""
    document = core.ingest(req.uri)
    return {"document_id": document.document_id, "state": document.state}


@app.post("/upload", dependencies=_KORUMALI)
async def upload_documents(files: List[UploadFile] = File(...),
                           core: GraphRAGCore = Depends(get_core)):
    """Yüklenen bir veya birden çok dosyayı kaydedip ingest eder."""
    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    results = []
    for file in files:
        # basename: dosya adındaki olası "../" yol saldırılarını engeller.
        safe_name = os.path.basename(file.filename or "belge")
        dest = os.path.join(upload_dir, safe_name)
        with open(dest, "wb") as fh:
            fh.write(await file.read())
        document = core.ingest(dest)
        results.append({"document_id": document.document_id,
                        "name": safe_name, "state": document.state.value})
    return {"documents": results}


# --- Sorgular ----------------------------------------------------------------

@app.post("/ask", dependencies=_KORUMALI)
def ask(req: AskRequest, core: GraphRAGCore = Depends(get_core)):
    """Arşive bir soru sorar (RAG) — cevabı KAYNAKLARIYLA birlikte döndürür."""
    result = core.answer_with_sources(req.question)

    # Kaynakları, kullanıcının tanıdığı belge adlarıyla zenginleştir.
    names = {d["document_id"]: d["name"] for d in core.documents()}
    for source in result["sources"]:
        source["document_name"] = names.get(source["document_id"], "belge")
    return result


@app.get("/connection", dependencies=_KORUMALI)
def connection(source: str, target: str, core: GraphRAGCore = Depends(get_core)):
    """İki varlık arasındaki graf bağlantısını YAPILANDIRILMIŞ olarak döndürür."""
    return core.find_connection_detailed(source, target)


@app.get("/entities", dependencies=_KORUMALI)
def entities(core: GraphRAGCore = Depends(get_core)):
    """Graftaki tüm varlıklar (varlık gezgini ve otomatik tamamlama için)."""
    return {"entities": core.entities()}


@app.get("/audit", dependencies=_KORUMALI)
def audit(core: GraphRAGCore = Depends(get_core)):
    """KVKK denetim kaydı: hangi tip kişisel veri, ne zaman maskelendi."""
    return {"events": core.audit_events()}


# --- Web arayüzü (frontend) --------------------------------------------------
# static/index.html'i sunar. Aynı origin olduğu için tarayıcıdaki JavaScript,
# yukarıdaki endpoint'leri CORS derdi olmadan çağırabilir.
_STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/app", StaticFiles(directory=_STATIC_DIR, html=True), name="ui")
