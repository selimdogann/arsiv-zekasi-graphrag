"""
FastAPI web servisi — GraphRAGCore'u HTTP üzerinden dışa açar.

Bu dosya, projeyi "çalışan bir servise" çevirir: `demo.py` çekirdeği terminalden
sürüyordu; bu API ise aynı çekirdeği HTTP'den sürer. GraphRAGCore burada da
değişmez — bu dosya sadece yeni bir "giriş kapısı".

Çekirdek, `get_core` bağımlılığı (Depends) üzerinden verilir. Böylece testlerde
gerçek Ollama'ya gitmeden, sahte bir çekirdekle değiştirilebilir.

Çalıştırma:
    uvicorn graphrag.api:app --reload
Sonra tarayıcıda: http://localhost:8000/docs
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graphrag.application.graphrag_core import GraphRAGCore
from graphrag.composition import build_core

app = FastAPI(title="GraphRAG Arşiv Zekâsı API")

# Çekirdek İLK istekte bir kez kurulur (lazy singleton) ve tüm istekler paylaşır.
_core: "GraphRAGCore | None" = None


def get_core() -> GraphRAGCore:
    """Endpoint'lere çekirdeği veren bağımlılık. Testte override edilebilir."""
    global _core
    if _core is None:
        _core = build_core()
    return _core


# --- İstek gövdelerinin (JSON) şekli: Pydantic modelleri ---------------------

class IngestRequest(BaseModel):
    uri: str            # yüklenecek belgenin yolu


class AskRequest(BaseModel):
    question: str


# --- Endpoint'ler ------------------------------------------------------------

@app.get("/")
def health():
    """Sağlık kontrolü: servis ayakta mı?"""
    return {"status": "ok"}


@app.post("/documents")
def ingest_document(req: IngestRequest, core: GraphRAGCore = Depends(get_core)):
    """Bir belgeyi sisteme yükler (ingest)."""
    document = core.ingest(req.uri)
    return {"document_id": document.document_id, "state": document.state}


@app.post("/ask")
def ask(req: AskRequest, core: GraphRAGCore = Depends(get_core)):
    """Arşive bir soru sorar (RAG)."""
    return {"answer": core.answer(req.question)}


@app.get("/connection")
def connection(source: str, target: str, core: GraphRAGCore = Depends(get_core)):
    """İki varlık arasındaki graf bağlantısını bulur."""
    return {"result": core.find_connection(source, target)}


# --- Web arayüzü (frontend) --------------------------------------------------
# static/index.html'i sunar. Aynı sunucudan geldiği için tarayıcıdaki JavaScript,
# yukarıdaki endpoint'leri (/ask, /documents, /connection) CORS derdi olmadan
# çağırabilir. Adres: http://localhost:8000/app/
_STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/app", StaticFiles(directory=_STATIC_DIR, html=True), name="ui")
