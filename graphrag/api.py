"""
FastAPI web servisi — GraphRAGCore'u HTTP üzerinden dışa açar.

Bu dosya, çekirdeği HTTP üzerinden sunan "giriş kapısı"dır. GraphRAGCore
burada da değişmez; HTTP'ye özgü işler (girdi doğrulama, hata → durum kodu
çevirisi, dosya kaydetme) yalnızca burada yapılır.

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
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graphrag.application.graphrag_core import GraphRAGCore
from graphrag.composition import build_core
from graphrag.config import get_settings
from graphrag.domain.exceptions import IngestionError
from graphrag.infrastructure.llm.ollama_llm import CHAT_MODEL, EMBED_MODEL

OLLAMA_BASE = "http://localhost:11434"

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD_DIR = os.path.join(_ROOT_DIR, "uploads")
# `POST /documents` yalnızca bu klasördeki örnek belgeleri yükleyebilir.
_ORNEK_DIR = os.path.realpath(os.path.join(_ROOT_DIR, "ornek_belgeler"))

# Desteklenen uzantılar ve tek dosya için üst sınır. Kontrol, dosya diske
# yazılmadan ÖNCE yapılır: reddedilecek bir dosya sunucuda iz bırakmaz.
DESTEKLENEN_UZANTILAR = {".txt", ".pdf", ".docx"}
AZAMI_DOSYA_BAYT = 25 * 1024 * 1024   # 25 MB

app = FastAPI(title="Arşiv Zekâsı API", version="1.1.0")


# --- Hata → HTTP durum kodu çevirisi -----------------------------------------
# Çekirdek HTTP'yi bilmez; kendi hatalarını fırlatır. Hangisinin kullanıcıya
# hangi kodla ve hangi Türkçe mesajla döneceğine yalnızca burada karar verilir.
# Bunlar olmadan her hata, arayüzde anlamsız bir "sunucu 500" olarak görünüyordu.

@app.exception_handler(IngestionError)
def _ingestion_hatasi(_: Request, exc: IngestionError):
    """Okunamayan / desteklenmeyen / boş belge → 400 + nedenini söyleyen mesaj."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(requests.RequestException)
def _llm_ulasilamiyor(_: Request, exc: requests.RequestException):
    """Ollama kapalıysa → 503: sorun bizde değil, bağımlı serviste."""
    return JSONResponse(status_code=503, content={
        "detail": "Yapay zekâ servisine (Ollama) ulaşılamıyor. "
                  "`python3 scripts/baslat.py` ile başlatıp tekrar deneyin."})

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


def _arsivde_var(core: GraphRAGCore, ad: str) -> bool:
    """Aynı adlı bir belge zaten arşivde mi? (çift yüklemeyi önler)"""
    return any(d["name"] == ad for d in core.documents())


@app.post("/documents", dependencies=_KORUMALI)
def ingest_document(req: IngestRequest, core: GraphRAGCore = Depends(get_core)):
    """`ornek_belgeler/` klasöründeki bir örnek belgeyi ingest eder.

    Yol, proje köküne göre (ya da mutlak) verilir ve MUTLAKA örnek belgeler
    klasörünün içinde kalmalıdır. Kısıt olmasaydı anahtar sahibi biri,
    sunucudaki herhangi bir .txt/.pdf/.docx dosyasını arşive alıp içeriğini
    sorularla okuyabilirdi. Kendi dosyalarınız için `POST /upload` kullanın.
    """
    hedef = os.path.realpath(os.path.join(_ROOT_DIR, req.uri))
    if os.path.commonpath([hedef, _ORNEK_DIR]) != _ORNEK_DIR:
        raise HTTPException(status_code=400, detail=(
            "Bu uç yalnızca ornek_belgeler/ klasöründeki dosyaları yükler; "
            "kendi dosyalarınız için /upload kullanın."))
    if _arsivde_var(core, os.path.basename(hedef)):
        raise HTTPException(status_code=409, detail="Bu belge zaten arşivde.")
    document = core.ingest(hedef)
    return {"document_id": document.document_id, "state": document.state}


@app.delete("/documents/{document_id}", dependencies=_KORUMALI)
def delete_document(document_id: str, core: GraphRAGCore = Depends(get_core)):
    """Bir belgeyi ve ondan türeyen parça/varlık/ilişkileri arşivden siler."""
    if not core.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")
    return {"deleted": document_id}


@app.delete("/documents", dependencies=_KORUMALI)
def clear_documents(core: GraphRAGCore = Depends(get_core)):
    """Arşivdeki TÜM belgeleri siler (demo/sunum sonrası temizlik)."""
    return {"deleted": core.clear_archive()}


@app.post("/upload", dependencies=_KORUMALI)
async def upload_documents(files: List[UploadFile] = File(...),
                           core: GraphRAGCore = Depends(get_core)):
    """Yüklenen bir veya birden çok dosyayı kaydedip ingest eder.

    Her dosya AYRI değerlendirilir: biri reddedilse bile diğerleri yüklenir.
    Yanıt iki liste döndürür — `documents` (başarılı) ve `errors` (dosya adı +
    nedeni) — böylece arayüz "3 belge eklendi, 1 atlandı: neden" diyebilir.
    """
    os.makedirs(_UPLOAD_DIR, exist_ok=True)

    results, errors = [], []
    for file in files:
        # basename: dosya adındaki olası "../" yol saldırılarını engeller.
        safe_name = os.path.basename(file.filename or "belge")

        def reddet(neden: str) -> None:
            errors.append({"name": safe_name, "detail": neden})

        uzanti = os.path.splitext(safe_name)[1].lower()
        if uzanti not in DESTEKLENEN_UZANTILAR:
            reddet(f"Desteklenmeyen dosya türü ({uzanti or 'uzantısız'}); "
                   ".txt, .pdf veya .docx yükleyin.")
            continue
        if _arsivde_var(core, safe_name):
            reddet("Bu adla bir belge zaten arşivde.")
            continue
        icerik = await file.read()
        if len(icerik) > AZAMI_DOSYA_BAYT:
            reddet("Dosya 25 MB sınırını aşıyor.")
            continue

        dest = os.path.join(_UPLOAD_DIR, safe_name)
        with open(dest, "wb") as fh:
            fh.write(icerik)
        try:
            document = core.ingest(dest)
        except IngestionError as exc:
            os.remove(dest)          # işlenemeyen dosya sunucuda kalmasın
            reddet(str(exc))
            continue
        except Exception:
            os.remove(dest)
            raise                    # ör. Ollama kapalı → 503 (yukarıdaki işleyici)
        results.append({"document_id": document.document_id,
                        "name": safe_name, "state": document.state.value})
    return {"documents": results, "errors": errors}


# --- Sorgular ----------------------------------------------------------------

@app.post("/ask", dependencies=_KORUMALI)
def ask(req: AskRequest, core: GraphRAGCore = Depends(get_core)):
    """Arşive bir soru sorar (RAG) — cevabı KAYNAKLARIYLA birlikte döndürür."""
    soru = req.question.strip()
    if not soru:   # boş soru LLM'e hiç gitmesin (boşuna 5-7 sn bekleme)
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")
    result = core.answer_with_sources(soru)

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
_STATIC_DIR = os.path.join(_ROOT_DIR, "static")
app.mount("/app", StaticFiles(directory=_STATIC_DIR, html=True), name="ui")
