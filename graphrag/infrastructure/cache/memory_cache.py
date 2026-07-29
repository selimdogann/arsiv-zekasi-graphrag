"""
InMemoryCache — `ICache`'in bellek-içi (sözlük tabanlı) uygulaması.

`hits`/`misses` sayaçları, önbelleğin gerçekten işe yarayıp yaramadığını
gözlemlemek için tutulur (bir sözleşme zorunluluğu değil, sadece pratik bir ek).
"""
from __future__ import annotations

from typing import Dict, Optional

from graphrag.domain.interfaces import ICache


class InMemoryCache(ICache):
    def __init__(self) -> None:
        self._store: Dict[str, object] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[object]:
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.misses += 1
        return None

    def set(self, key: str, value: object) -> None:
        self._store[key] = value
