"""
OllamaLanguageModel — gerçek, yerel LLM istemcisi.

Ollama'nın REST API'sine (http://localhost:11434) HTTP isteği göndererek,
gerçek bir dil modelinden (llama3.2) metin üretimi alır.
"""
from __future__ import annotations

import hashlib

import requests

from graphrag.domain.interfaces import ILanguageModel

_BASE_URL = "http://localhost:11434"
_MODEL = "llama3.2"
_DIM = 16


class OllamaLanguageModel(ILanguageModel):
    def complete(self, prompt: str) -> str:
        response = requests.post(
            f"{_BASE_URL}/api/generate",
            json={"model": _MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        data = response.json()
        return data["response"]

    def embed(self, text: str):
        # Embedding için basit hash yöntemini koruyoruz — vektör aramanın
        # matematiği (kosinüs benzerliği), sayıların NEREDEN geldiğinden
        # bağımsız çalışır; bu kısmı ileride gerçek embedding API'sine de
        # bağlayabiliriz.
        vec = [0.0] * _DIM
        for word in text.lower().split():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            vec[h % _DIM] += 1.0
        return tuple(vec)
