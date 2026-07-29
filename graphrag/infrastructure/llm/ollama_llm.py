"""
OllamaLanguageModel — gerçek, yerel LLM istemcisi.

`/api/chat` uç noktasını kullanır — sohbet formatı (system/user), modelin
talimatlara (özellikle "sadece bağlamı kullan, uydurma") uymasını
`/api/generate`'e göre belirgin ölçüde güçlendirir.
"""
from __future__ import annotations


import requests

from graphrag.domain.interfaces import ILanguageModel

_BASE_URL = "http://localhost:11434"
_MODEL = "llama3.2"
_EMBED_MODEL = "bge-m3"


_SYSTEM_PROMPT = (
    "Sen bir kurumsal arşiv asistanısın. SADECE sana verilen BAĞLAM'a "
    "dayanarak cevap ver. Bağlamda olmayan hiçbir bilgiyi UYDURMA. "
    "Bağlamda cevap yoksa açıkça 'Bu bilgi arşivde bulunamadı' de."
)


class OllamaLanguageModel(ILanguageModel):
    def complete(self, prompt: str) -> str:
        response = requests.post(
            f"{_BASE_URL}/api/chat",
            json={
                "model": _MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=60,
        )
        data = response.json()
        return data["message"]["content"]

    def embed(self, text: str):
        response = requests.post(
            f"{_BASE_URL}/api/embeddings",
            json={"model": _EMBED_MODEL, "prompt": text},
            timeout=60,
        )
        data = response.json()
        return tuple(data["embedding"])

