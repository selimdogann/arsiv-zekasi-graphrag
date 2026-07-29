"""
Document durum makinesi (DFA) için testler.

Yeni teknik: `pytest.raises(...)` — "bu kod bloğu ŞU hatayı fırlatmalı"
diye test etmenin yolu. Fırlatmazsa test kırılır.
"""
import pytest

from graphrag.domain.entities import Document, DocumentState
from graphrag.domain.exceptions import InvalidStateTransitionError


def test_gecerli_gecis_calisir():
    doc = Document()
    doc.transition_to(DocumentState.PARSING)
    assert doc.state == DocumentState.PARSING


def test_yasak_gecis_hata_firlatir():
    doc = Document()  # başlangıç durumu: RECEIVED
    # RECEIVED'dan doğrudan PARSED'e geçmek YASAK -> hata beklenir
    with pytest.raises(InvalidStateTransitionError):
        doc.transition_to(DocumentState.PARSED)


def test_gecis_gecmise_kaydedilir():
    doc = Document()
    doc.transition_to(DocumentState.PARSING)
    assert len(doc.history) == 1
