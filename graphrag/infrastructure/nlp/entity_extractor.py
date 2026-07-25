"""
SimpleEntityExtractor — regex tabanlı, deterministik varlık çıkarımı.

LLM'e ihtiyaç duymadan, büyük harfle başlayan kelime gruplarını (özel isim
adayları) yakalar. Basit ama üretime hazır bir başlangıç noktası.
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
