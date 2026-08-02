"""
Reciprocal Rank Fusion (RRF) — birden çok sıralı listeyi tek sıralamaya birleştirir.

Neden gerekli? Vektör araması kosinüs skoru (0-1), BM25 farklı ölçekte skor
(0-20+) üretir; bunları doğrudan toplayamayız. RRF, skor yerine SIRA numarasını
kullanır (karşılaştırılabilir): bir öğenin skoru, her listede 1/(k + sıra)
toplamıdır. Herhangi bir listede üstte olan iyi puan alır; ikisinde de üstteyse
en iyisi. Basit, ölçekten bağımsız ve endüstri standardı.
"""
from __future__ import annotations

from typing import Dict, List


def reciprocal_rank_fusion(rankings: List[List[str]], k: int = 60) -> List[str]:
    """Sıralı id listelerini RRF ile tek bir sıralı id listesine indirger.

    `rankings`: her biri EN İYİDEN kötüye sıralı id listesi.
    Dönüş: birleşik skora göre en iyiden kötüye sıralı, benzersiz id listesi.
    """
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda item_id: scores[item_id], reverse=True)
