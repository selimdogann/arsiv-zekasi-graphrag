"""
CachedLanguageModel — bir `ILanguageModel`'i "sarmalayan" (decorator deseni)
önbellekli sürüm.

Dinamik programlamanın temel fikri: "aynı alt problemi iki kez çözme."
Aynı metin/prompt birden fazla kez istenirse, GERÇEK LLM'e (yavaş, ağ
gerektiren bir işlem) tekrar gidilmez — önbellekten anında döner.

Neden ayrı bir SINIF (fonksiyon değil)? Çünkü kendisi de `ILanguageModel`
sözleşmesini uyguluyor — yani `GraphRAGCore`'un gözünde, sarmaladığı gerçek
LLM'den (`OllamaLanguageModel`) FARKSIZ. `composition.py`'de gerçek LLM'i bu
sınıfla "sarmalamak" yeterli; hiçbir başka dosya bunun farkında bile değil.
"""
from __future__ import annotations

from graphrag.domain.interfaces import ICache, ILanguageModel


class CachedLanguageModel(ILanguageModel):
    def __init__(self, inner: ILanguageModel, cache: ICache) -> None:
        self._inner = inner
        self._cache = cache

    def complete(self, prompt: str) -> str:
        key = f"complete:{prompt}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._inner.complete(prompt)
        self._cache.set(key, result)
        return result

    def embed(self, text: str):
        key = f"embed:{text}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._inner.embed(text)
        self._cache.set(key, result)
        return result
