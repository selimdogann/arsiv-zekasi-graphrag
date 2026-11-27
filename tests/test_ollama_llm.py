"""
OllamaLanguageModel'in hata çevirisi için testler.

Gerçek Ollama'ya gidilmez: `requests.post` sahte bir yanıtla değiştirilir.
Amaç, Ollama'nın hata yanıtlarının (ör. model indirilmemiş → 404) anlamsız bir
KeyError yerine anlaşılır bir alan hatasına (LanguageModelError) dönüşmesidir.
"""
import json

import pytest
import requests

from graphrag.domain.exceptions import LanguageModelError
from graphrag.infrastructure.llm import ollama_llm
from graphrag.infrastructure.llm.ollama_llm import OllamaLanguageModel


def _sahte_yanit(durum, govde):
    r = requests.Response()
    r.status_code = durum
    r._content = json.dumps(govde).encode()
    return r


def test_model_yoksa_pull_komutunu_soyleyen_hata(monkeypatch):
    monkeypatch.setattr(ollama_llm.requests, "post", lambda *a, **k: _sahte_yanit(
        404, {"error": "model \"bge-m3\" not found, try pulling it first"}))
    with pytest.raises(LanguageModelError) as hata:
        OllamaLanguageModel().embed("metin")
    assert "ollama pull bge-m3" in str(hata.value)


def test_diger_hatalar_durum_koduyla_bildirilir(monkeypatch):
    monkeypatch.setattr(ollama_llm.requests, "post",
                        lambda *a, **k: _sahte_yanit(500, {"error": "bellek yetersiz"}))
    with pytest.raises(LanguageModelError) as hata:
        OllamaLanguageModel().complete("soru")
    assert "500" in str(hata.value) and "bellek yetersiz" in str(hata.value)


def test_basarili_yanit_icerigi_doner(monkeypatch):
    monkeypatch.setattr(ollama_llm.requests, "post",
                        lambda *a, **k: _sahte_yanit(200, {"embedding": [0.1, 0.2]}))
    assert OllamaLanguageModel().embed("metin") == (0.1, 0.2)
