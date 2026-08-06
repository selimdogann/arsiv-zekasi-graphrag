"""
LlmRelationExtractor — `IRelationExtractor`'ın LLM tabanlı uygulaması.

Varlık çıkarımı "belgede kimler var" sorusunu yanıtlar; bu sınıf ise
"aralarındaki ilişki NE" sorusunu. Sonuçta graf kenarları anlam taşır:

    Acme Holding --anlaştı--> Proje Zeus --teknik destek verdi--> Gamma Danışmanlık

İlişki çıkarılamayan varlık çiftleri için çekirdek, eskisi gibi etiketsiz
"aynı belgede birlikte geçti" (co-occurrence) kenarı kurmayı sürdürür; yani
bu katman mevcut davranışı bozmaz, üzerine anlam ekler.
"""
from __future__ import annotations

from typing import List

from graphrag.domain.entities import Relation
from graphrag.domain.interfaces import ILanguageModel, IRelationExtractor
from graphrag.domain.text_tr import canonical_entity_key

_PROMPT = (
    "Aşağıdaki METİN'de, verilen VARLIKLAR arasındaki ilişkileri çıkar.\n"
    "Her satıra bir ilişki yaz, tam olarak şu biçimde:\n"
    "VARLIK1 | ilişki | VARLIK2\n\n"
    "Kurallar:\n"
    "- İlişki kısmı KISA bir fiil öbeği olsun (en fazla 3 kelime): "
    "'anlaştı', 'teknik destek verdi', 'raporu hazırladı'.\n"
    "- Yalnızca METİN'de AÇIKÇA belirtilen ilişkileri yaz; hiçbir şey UYDURMA.\n"
    "- Yalnızca VARLIKLAR listesindeki adları kullan.\n"
    "- İlişki yoksa hiçbir şey yazma.\n\n"
    "VARLIKLAR: {entities}\n\n"
    "METİN: {text}\n\n"
    "İLİŞKİLER:"
)

# İlişki etiketi bu kadar uzunsa cümle kopyalanmıştır, etiket değildir.
_AZAMI_KELIME = 4


class LlmRelationExtractor(IRelationExtractor):
    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def extract(self, text: str, entities: List[str]) -> List[Relation]:
        if len(entities) < 2:
            return []      # ilişki için en az iki varlık gerekir

        cevap = self._llm.complete(
            _PROMPT.format(entities=", ".join(entities), text=text))

        # Varlıkları kanonik anahtarlarıyla eşle: LLM adı farklı yazsa da tut.
        gecerli = {canonical_entity_key(e): e for e in entities}

        iliskiler: List[Relation] = []
        for satir in cevap.splitlines():
            parcalar = [p.strip() for p in satir.split("|")]
            if len(parcalar) != 3:
                continue
            ozne, iliski, nesne = parcalar
            if not iliski or len(iliski.split()) > _AZAMI_KELIME:
                continue

            # TEMELLENDİRME: yalnızca gerçekten çıkarılmış varlıklar arasında
            # ilişki kurulur — LLM'in uydurduğu adlar grafa girmez.
            ozne_k, nesne_k = canonical_entity_key(ozne), canonical_entity_key(nesne)
            if ozne_k not in gecerli or nesne_k not in gecerli or ozne_k == nesne_k:
                continue

            iliskiler.append(Relation(source=gecerli[ozne_k],
                                      relation=iliski,
                                      target=gecerli[nesne_k]))
        return iliskiler
