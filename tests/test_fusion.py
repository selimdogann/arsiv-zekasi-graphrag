"""
Reciprocal Rank Fusion (RRF) için testler — saf, deterministik fonksiyon.
"""
from graphrag.application.fusion import reciprocal_rank_fusion


def test_tek_liste_sirayi_korur():
    assert reciprocal_rank_fusion([["a", "b", "c"]]) == ["a", "b", "c"]


def test_her_iki_listede_ilk_olan_en_tepede():
    list1 = ["x", "y", "z"]
    list2 = ["x", "z", "y"]
    assert reciprocal_rank_fusion([list1, list2])[0] == "x"


def test_iki_listede_birlikte_ustte_olan_kazanir():
    # b: 1.listede 2., 2.listede 1. → toplamda a ve c'den önde olmalı
    list1 = ["a", "b", "c"]
    list2 = ["b", "c", "a"]
    assert reciprocal_rank_fusion([list1, list2])[0] == "b"


def test_bos_girdi_bos_doner():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []
