"""
MockLanguageModel — ağa hiç çıkmayan, deterministik bir sahte LLM.

Gerçek bir yerel LLM sunucusu kurulu olmadan `ILanguageModel` sözleşmesini
test edebilmek için yazılmıştır.
"""
from __future__ import annotations

import hashlib

from graphrag.domain.interfaces import ILanguageModel

_DIM = 16  # embedding boyutu (gerçek LLM'lerde yüzlerce olur, biz küçük tutuyoruz)


class MockLanguageModel(ILanguageModel):
    def complete(self, prompt: str) -> str:
        return f"[SAHTE YANIT] Şu soruya cevap üretildi: {prompt}"

    def embed(self, text: str):
        vec = [0.0] * _DIM
        for word in text.lower().split():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            vec[h % _DIM] += 1.0
        return tuple(vec)
