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

# Model, isteksiz kalınca varsayılan olarak ~4 dakikada bellekten düşer ve
# sonraki ilk soru ~12 saniye sürer. Sunum/demo sırasında bu bekleme kötü
# bir deneyim yarattığı için modeli daha uzun süre bellekte tutuyoruz.
_KEEP_ALIVE = "30m"

# Aktif modeller — arayüzün durum çubuğunda gerçek değeri gösterebilmesi için
# dışa açık (public) tutulur.
CHAT_MODEL = "qwen2.5:7b"
EMBED_MODEL = "bge-m3"


# Nötr, göreve özgü OLMAYAN sistem talimatı.
#
# Önceden burada "sen bir arşiv asistanısın, cevap yoksa 'bulunamadı' de" gibi
# soru-cevaba özgü bir talimat vardı. Bu, UYGULAMA katmanına ait bir kuralın
# altyapıya sızmasıydı ve varlık çıkarımını bozuyordu: model, çıkarım isteğini
# de "cevaplanacak soru" sanıp "Bu bilgi arşivde bulunamadı" döndürebiliyordu.
# Göreve özgü talimatlar artık çağıranın prompt'unda yer alır.
_SYSTEM_PROMPT = (
    "Türkçe kurumsal belgelerle çalışan bir asistansın. Kendisinden istenen "
    "biçimde, kısa ve doğrudan yanıt ver."
)


class OllamaLanguageModel(ILanguageModel):
    def complete(self, prompt: str) -> str:
        response = requests.post(
            f"{_BASE_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "keep_alive": _KEEP_ALIVE,
            },
            timeout=60,
        )
        data = response.json()
        return data["message"]["content"]

    def embed(self, text: str):
        response = requests.post(
            f"{_BASE_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text, "keep_alive": _KEEP_ALIVE},
            timeout=60,
        )
        data = response.json()
        return tuple(data["embedding"])

