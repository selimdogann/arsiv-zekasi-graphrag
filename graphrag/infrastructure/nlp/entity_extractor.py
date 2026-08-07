"""
SimpleEntityExtractor — regex tabanlı, DETERMİNİSTİK varlık çıkarımı.

Büyük harfle başlayan kelime gruplarını (özel isim adayları) yakalar; LLM'e
ihtiyaç duymaz.

NEREDE KULLANILIR? Üretimde `LlmEntityExtractor` tercih edilir (bağlamı anlar,
daha temiz sonuç verir). Bu sınıf ise `IEntityExtractor` portunun deterministik
ikinci uygulamasıdır ve **entegrasyon testlerinde** kullanılır: testlerin
çalışması için ne Ollama'ya ne ağa ihtiyaç duyulur, sonuç her çalıştırmada
aynıdır. Aynı porta iki farklı adaptör takılabilmesi, Ports & Adapters
mimarisinin somut karşılığıdır.
"""
from __future__ import annotations

import re
from typing import List

from graphrag.domain.interfaces import IEntityExtractor

_PATTERN = re.compile(
    r"\b([A-ZĞÜŞİÖÇ][\wğüşıöç]+(?:\s+[A-ZĞÜŞİÖÇ][\wğüşıöç]+)*)\b"
)


class SimpleEntityExtractor(IEntityExtractor):
    def extract(self, text: str) -> List[str]:
        candidates = _PATTERN.findall(text)
        # Tekrarları kaldır, ama bulunma sırasını koru
        seen = set()
        result = []
        for name in candidates:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result
