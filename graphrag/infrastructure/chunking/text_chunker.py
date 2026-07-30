"""
SlidingWindowChunker — `IChunker`'ın kayan pencere (sliding window) uygulaması.

Uzun bir metni, yaklaşık sabit boyutlu (karakter sayısına göre) parçalara böler
ama KELİMELERİ ortadan bölmez: metni kelimelere ayırıp, bir parça dolana kadar
kelime kelime doldurur. Parça dolunca yeni parçaya geçer.

Ardışık parçalar arasında bir miktar ÖRTÜŞME (overlap) bırakır: yeni parça,
bir önceki parçanın SON birkaç kelimesiyle başlar. Böylece anlam bir parçanın
sınırında kopmaz — bir cümle iki parçaya bölünse bile, bağlam en az bir
parçada bütün hâlde bulunur.

Neden kelime bazlı? Basit, deterministik ve kelime bütünlüğünü korur. Daha
akıllı stratejiler (cümle/anlamsal bölme) ileride SADECE bu sınıfın yerine
yeni bir IChunker uygulaması yazılarak eklenebilir — çağıran kod (GraphRAGCore)
hiç değişmez.
"""
from __future__ import annotations

from typing import List

from graphrag.domain.interfaces import IChunker


class SlidingWindowChunker(IChunker):
    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size pozitif olmalı")
        if not (0 <= overlap < chunk_size):
            raise ValueError("overlap, 0 ile chunk_size arasında olmalı")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(self, text: str) -> List[str]:
        words = text.split()
        if not words:
            return []

        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for word in words:
            # +1: kelimeler arasındaki boşluğu da say. Parça dolduysa (ve boş
            # değilse) mevcut parçayı kapat, örtüşme kadar kelimeyle yeniden başla.
            if current and current_len + len(word) + 1 > self._chunk_size:
                chunks.append(" ".join(current))
                current, current_len = self._overlap_tail(current)

            current.append(word)
            current_len += len(word) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks

    def _overlap_tail(self, words: List[str]) -> "tuple[List[str], int]":
        """Bir sonraki parçanın başına taşınacak son kelimeleri seçer
        (toplam uzunlukları overlap sınırını aşmayacak şekilde)."""
        tail: List[str] = []
        length = 0
        for word in reversed(words):
            if length + len(word) + 1 > self._overlap:
                break
            tail.insert(0, word)
            length += len(word) + 1
        return tail, length
