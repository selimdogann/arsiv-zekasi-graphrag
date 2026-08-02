"""
LlmEntityExtractor için testler.

Gerçek LLM'e gitmeden, sabit yanıt döndüren SAHTE bir LLM ile çıktı ayrıştırma
(parse) mantığını test ederiz: satırlara böl, madde işareti/numara temizle,
boşları ve tekrarları at.
"""
from graphrag.domain.interfaces import ILanguageModel
from graphrag.infrastructure.nlp.llm_entity_extractor import LlmEntityExtractor


class _SahteLLM(ILanguageModel):
    def __init__(self, cevap: str) -> None:
        self._cevap = cevap

    def complete(self, prompt: str) -> str:
        return self._cevap

    def embed(self, text: str):
        return ()


def test_satirlari_varlik_listesine_cevirir():
    llm = _SahteLLM("Acme Holding\nProje Zeus\nBeta Firması")
    assert LlmEntityExtractor(llm).extract("...") == \
        ["Acme Holding", "Proje Zeus", "Beta Firması"]


def test_madde_isareti_ve_numaralandirmayi_temizler():
    llm = _SahteLLM("- Acme Holding\n2. Proje Zeus\n* Beta Firması")
    assert LlmEntityExtractor(llm).extract("...") == \
        ["Acme Holding", "Proje Zeus", "Beta Firması"]


def test_bos_satirlari_ve_tekrarlari_atar():
    llm = _SahteLLM("Acme Holding\n\nAcme Holding\n   \nProje Zeus")
    assert LlmEntityExtractor(llm).extract("...") == ["Acme Holding", "Proje Zeus"]
