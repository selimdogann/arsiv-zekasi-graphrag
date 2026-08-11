"""
InMemoryGraphStore için testler — özellikle KÖKEN (provenance) mantığı.

Bir varlık birden çok belgede geçebilir. Bu yüzden depo, her düğüm ve kenar
için "beni hangi belgeler destekliyor" bilgisini tutar; belge silindiğinde
yalnızca DESTEKSİZ kalanlar grafı terk eder. Aşağıdaki testler tam olarak bu
davranışı sabitler.
"""
import pytest

from graphrag.domain.entities import GraphEdge, GraphNode
from graphrag.infrastructure.graph.graph_store import InMemoryGraphStore


def test_ayni_kenar_iki_kez_eklenince_cogalmaz():
    """upsert 'ekle-VEYA-güncelle' demektir; aynı kenar iki satır olmamalı."""
    graph = InMemoryGraphStore()
    graph.upsert_edge(GraphEdge("a", "b", 0.7, 0.5))
    graph.upsert_edge(GraphEdge("a", "b", 0.2, 0.8, "anlaştı"))

    assert graph.edge_count() == 1
    assert graph.neighbors("a")[0].relation == "anlaştı"   # son hâl geçerli


def test_paylasilan_dugum_bir_belge_silinince_kalir():
    graph = InMemoryGraphStore()
    graph.upsert_node(GraphNode("zeus", "Proje Zeus"), "d1")
    graph.upsert_node(GraphNode("zeus", "Proje Zeus"), "d2")

    graph.delete_document("d2")

    assert graph.get_node("zeus").label == "Proje Zeus"


def test_desteksiz_kalan_dugum_ve_kenar_silinir():
    graph = InMemoryGraphStore()
    graph.upsert_node(GraphNode("gamma", "Gamma"), "d2")
    graph.upsert_node(GraphNode("zeus", "Proje Zeus"), "d2")
    graph.upsert_edge(GraphEdge("zeus", "gamma", 0.7, 0.5), "d2")

    graph.delete_document("d2")

    assert graph.all_nodes() == []
    assert graph.edge_count() == 0
    with pytest.raises(KeyError):
        graph.get_node("gamma")


def test_silinen_dugume_giden_kenar_geride_kalmaz():
    """Öksüz kenar kalırsa Dijkstra var olmayan bir düğüme yürümeye çalışır."""
    graph = InMemoryGraphStore()
    graph.upsert_node(GraphNode("acme", "Acme"), "d1")
    graph.upsert_node(GraphNode("gamma", "Gamma"), "d2")
    # Kenarın kökeni d1: normalde d2 silinse de kalırdı — ama hedefi yok oluyor.
    graph.upsert_edge(GraphEdge("acme", "gamma", 0.7, 0.5), "d1")

    graph.delete_document("d2")

    assert graph.neighbors("acme") == []


def test_kokensiz_dugum_silmeden_etkilenmez():
    """Köken verilmeden eklenen düğüm (eski kayıt) silmede yok olmamalı."""
    graph = InMemoryGraphStore()
    graph.upsert_node(GraphNode("eski", "Eski Kayıt"))
    graph.upsert_node(GraphNode("yeni", "Yeni"), "d1")

    graph.delete_document("d1")

    assert graph.get_node("eski").label == "Eski Kayıt"
    with pytest.raises(KeyError):
        graph.get_node("yeni")
