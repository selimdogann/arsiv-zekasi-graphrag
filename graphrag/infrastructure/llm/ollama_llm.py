"""
OllamaLanguageModel — gerçek, yerel LLM istemcisi.

`/api/chat` uç noktasını kullanır — sohbet formatı (system/user), modelin
talimatlara (özellikle "sadece bağlamı kullan, uydurma") uymasını
`/api/generate`'e göre belirgin ölçüde güçlendirir.
"""
from __future__ import annotations


import requests

from graphrag.domain.exceptions import LanguageModelError
from graphrag.domain.interfaces import ILanguageModel

_BASE_URL = "http://localhost:11434"

# Model, isteksiz kalınca varsayılan olarak ~4 dakikada bellekten düşer ve
# sonraki ilk soru ~12 saniye sürer. Sunum/demo sırasında bu bekleme kötü
# bir deneyim yarattığı için modeli daha uzun süre bellekte tutuyoruz.
_KEEP_ALIVE = "30m"

# Sıcaklık (temperature) modelin ne kadar "yaratıcı" olacağını belirler.
# Ollama varsayılanı 0.8; bu, aynı metinden her seferinde FARKLI varlık ve
# ilişki çıkarılmasına yol açıyordu. Bu sistemde LLM'den beklenen yaratıcılık
# değil, metne sadakat: 0 ile çıktı olabildiğince kararlı hâle getirilir.
_OPTIONS = {"temperature": 0}

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


def _json(response: requests.Response, model: str) -> dict:
    """Ollama yanıtını çözer; hata yanıtını alan hatasına çevirir.

    Ollama, model indirilmemişse 404 + {"error": "..."} döner. Eskiden kod
    doğrudan data["embedding"] okuduğu için bu durum KeyError → anlamsız bir
    HTTP 500 oluyordu. Artık kullanıcıya ne yapması gerektiği söylenir.
    """
    if response.status_code == 404:
        raise LanguageModelError(
            f"Yapay zekâ modeli yüklü değil: `ollama pull {model}` ile indirin.")
    if not response.ok:
        hata = response.json().get("error", "") if response.content else ""
        raise LanguageModelError(f"Ollama isteği başarısız ({response.status_code}): {hata}")
    return response.json()


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
                "options": _OPTIONS,
            },
            timeout=60,
        )
        return _json(response, CHAT_MODEL)["message"]["content"]

    def embed(self, text: str):
        response = requests.post(
            f"{_BASE_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text, "keep_alive": _KEEP_ALIVE},
            timeout=60,
        )
        return tuple(_json(response, EMBED_MODEL)["embedding"])

