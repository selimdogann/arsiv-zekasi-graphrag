"""
LlmEntityExtractor — `IEntityExtractor`'ın LLM tabanlı uygulaması.

Regex yerine gerçek dil modeline (qwen) sorar: "bu metindeki kişiler, kurumlar,
projeler, yerler neler?" LLM bağlamı anladığı için, cümle başı kelimelerini
(ör. "Bu", "Taraflar") varlık sanmaz; çok kelimeli özel isimleri bütün yakalar.

Dürüst denge: LLM tabanlı çıkarım belirsizdir (çıktı değişebilir) ve bir LLM
çağrısı maliyeti getirir. Deterministik SimpleEntityExtractor bir seçenek
olarak korunur; bu adaptör aynı IEntityExtractor sözleşmesini uyguladığından
yalnızca composition'da değiştirilerek devreye alınır.
"""
from __future__ import annotations

from typing import List

from graphrag.domain.interfaces import IEntityExtractor, ILanguageModel

_PROMPT = (
    "Aşağıdaki METİN'de geçen önemli VARLIKLARI çıkar: kişiler, şirketler/"
    "kurumlar, projeler ve yerler. Kurallar:\n"
    "- Her varlığı AYRI SATIRA yaz, başka hiçbir açıklama ekleme.\n"
    "- Sadece METİN'de GEÇEN adları yaz; hiçbir şey UYDURMA.\n"
    "- Sıradan kelimeleri (fiil, bağlaç, cümle başı kelimesi) YAZMA.\n\n"
    "METİN: {text}\n\n"
    "VARLIKLAR:"
)


class LlmEntityExtractor(IEntityExtractor):
    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def extract(self, text: str) -> List[str]:
        response = self._llm.complete(_PROMPT.format(text=text))

        entities: List[str] = []
        for line in response.splitlines():
            # Madde işareti / numaralandırma / boşlukları temizle.
            name = line.strip().lstrip("-•*·").strip()
            # `name and` şart: boş satırda `"" in ".)"` True olup sonsuz döngü
            # yapmasın diye (Python'da boş string her metnin alt dizisidir).
            while name and (name[0].isdigit() or name[0] in ".)"):
                name = name[1:].strip()
            if name and name not in entities:
                entities.append(name)
        return entities
