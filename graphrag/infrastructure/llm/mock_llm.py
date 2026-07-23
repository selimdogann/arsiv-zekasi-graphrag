"""
MockLanguageModel — ağa hiç çıkmayan, deterministik bir sahte LLM.

Gerçek bir yerel LLM sunucusu kurulu olmadan `ILanguageModel` sözleşmesini
test edebilmek için yazılmıştır — az önce öğrendiğin "kontrol listesini
doldurma" kalıbının LLM'e uygulanmış hâli.
"""
from __future__ import annotations

from graphrag.domain.interfaces import ILanguageModel


class MockLanguageModel(ILanguageModel):
    def complete(self, prompt: str) -> str:
        return f"[SAHTE YANIT] Şu soruya cevap üretildi: {prompt}"
