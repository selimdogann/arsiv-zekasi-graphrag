"""
CachedLanguageModel için testler.

Burada gerçek bir LLM'e (Ollama'ya) ihtiyacımız yok — sadece "kaç kez
çağrıldım?" diye sayan SAHTE bir ILanguageModel yazıp, CachedLanguageModel'in
onu GEREKSİZ YERE ikinci kez çağırmadığını kanıtlıyoruz.
"""
from graphrag.domain.interfaces import ILanguageModel
from graphrag.infrastructure.cache.memory_cache import InMemoryCache
from graphrag.infrastructure.llm.cached_llm import CachedLanguageModel


class _SayanSahteLLM(ILanguageModel):
    """Her gerçek çağrıda sayacı bir artıran, test amaçlı sahte LLM."""

    def __init__(self) -> None:
        self.complete_cagri_sayisi = 0
        self.embed_cagri_sayisi = 0

    def complete(self, prompt: str) -> str:
        self.complete_cagri_sayisi += 1
        return f"cevap: {prompt}"

    def embed(self, text: str):
        self.embed_cagri_sayisi += 1
        return (1.0, 2.0, 3.0)


def test_ayni_prompt_ikinci_kez_gercek_llme_gitmez():
    sahte_llm = _SayanSahteLLM()
    cached = CachedLanguageModel(sahte_llm, InMemoryCache())

    cached.complete("merhaba")
    cached.complete("merhaba")   # AYNI prompt, ikinci kez

    assert sahte_llm.complete_cagri_sayisi == 1   # gerçek LLM SADECE 1 kez çağrıldı


def test_farkli_promptlar_ayri_ayri_cagrilir():
    sahte_llm = _SayanSahteLLM()
    cached = CachedLanguageModel(sahte_llm, InMemoryCache())

    cached.complete("soru bir")
    cached.complete("soru iki")   # FARKLI prompt

    assert sahte_llm.complete_cagri_sayisi == 2   # ikisi de gerçekten çağrılmalı


def test_embed_de_onbelleklenir():
    sahte_llm = _SayanSahteLLM()
    cached = CachedLanguageModel(sahte_llm, InMemoryCache())

    cached.embed("aynı metin")
    cached.embed("aynı metin")

    assert sahte_llm.embed_cagri_sayisi == 1


def test_onbellek_dogru_sonucu_dondurur():
    sahte_llm = _SayanSahteLLM()
    cached = CachedLanguageModel(sahte_llm, InMemoryCache())

    ilk_sonuc = cached.complete("test")
    ikinci_sonuc = cached.complete("test")

    assert ilk_sonuc == ikinci_sonuc == "cevap: test"
