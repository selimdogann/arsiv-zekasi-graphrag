"""
GraphSearchEngine (Dijkstra) için testler.

Test grafı: A'dan B'ye iki yol var:
  A -> X -> B (güven 0.9, 0.9) -> birleşik güven 0.81
  A -> Y -> B (güven 0.5, 0.5) -> birleşik güven 0.25
Dijkstra, ağırlığı (-log(güven)) en küçük olanı seçer -> en güvenilir yolu bulur.
"""
import math

import pytest

from graphrag.domain.entities import GraphEdge, GraphNode
from graphrag.domain.exceptions import PathNotFoundError
from graphrag.infrastructure.graph.graph_search_engine import GraphSearchEngine
from graphrag.infrastructure.graph.graph_store import InMemoryGraphStore


def _kurulu_graf():
    """Testler arası tekrarı önleyen yardımcı fonksiyon (test_ ile BAŞLAMIYOR,
    bu yüzden pytest bunu bir test SANMAZ, sadece bir hazırlık aracı sayar)."""
    graph = InMemoryGraphStore()
    for node_id in ["A", "X", "Y", "B"]:
        graph.upsert_node(GraphNode(node_id=node_id, label=node_id))

    def w(confidence):
        return -math.log(confidence)

    graph.upsert_edge(GraphEdge("A", "X", w(0.9), 0.9))
    graph.upsert_edge(GraphEdge("X", "B", w(0.9), 0.9))
    graph.upsert_edge(GraphEdge("A", "Y", w(0.5), 0.5))
    graph.upsert_edge(GraphEdge("Y", "B", w(0.5), 0.5))
    return graph


def test_en_guvenilir_yol_secilir():
    engine = GraphSearchEngine(_kurulu_graf())
    path = engine.shortest_path("A", "B")
    assert path.nodes == ("A", "X", "B")   # Y'li yol DEĞİL


def test_birlesik_guven_dogru_hesaplanir():
    engine = GraphSearchEngine(_kurulu_graf())
    path = engine.shortest_path("A", "B")
    assert path.probability == pytest.approx(0.81, abs=0.01)


def test_yol_yoksa_hata_firlatir():
    graph = _kurulu_graf()
    graph.upsert_node(GraphNode(node_id="Z", label="Z"))  # bağlantısız düğüm
    engine = GraphSearchEngine(graph)
    with pytest.raises(PathNotFoundError):
        engine.shortest_path("A", "Z")
