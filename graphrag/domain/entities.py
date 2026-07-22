"""
Document — evrağın yaşam döngüsünü yöneten toplama kökü (aggregate root).

Durum geçişleri deterministik bir sonlu durum makinesi (DFA) ile yönetilir:
`ALLOWED_TRANSITIONS`, hangi durumdan hangi duruma geçilebileceğini AÇIKÇA
tanımlar. İzin verilmeyen bir geçiş denendiğinde `InvalidStateTransitionError`
fırlatılır — böylece bir evrak asla "yarım işlenmiş" hâlde ileri gidemez.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Dict, List, Set, Tuple

from graphrag.domain.exceptions import InvalidStateTransitionError


class DocumentState(str, Enum):
    """Bir evrağın yaşam döngüsü boyunca alabileceği durumlar."""

    RECEIVED = "RECEIVED"    # sisteme alındı, henüz işlenmedi
    PARSING = "PARSING"      # metin çıkarımı sürüyor
    PARSED = "PARSED"        # metin hazır
    FAILED = "FAILED"        # kurtarılabilir hata; yeniden denenebilir
    ARCHIVED = "ARCHIVED"    # terminal durum


@dataclass
class Document:
    """Bir evrağı ve onun deterministik durum makinesini temsil eder."""

    ALLOWED_TRANSITIONS: Dict[DocumentState, Set[DocumentState]] = field(
        default_factory=lambda: {
            DocumentState.RECEIVED: {DocumentState.PARSING, DocumentState.FAILED},
            DocumentState.PARSING: {DocumentState.PARSED, DocumentState.FAILED},
            DocumentState.PARSED: {DocumentState.ARCHIVED},
            DocumentState.FAILED: {DocumentState.RECEIVED, DocumentState.ARCHIVED},
            DocumentState.ARCHIVED: set(),  # terminal: buradan çıkış yok
        },
        init=False,
        repr=False,
    )

    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    uri: str = ""
    raw_text: str = ""

    title: str = ""
    state: DocumentState = DocumentState.RECEIVED
    history: List[Tuple[DocumentState, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def can_transition_to(self, target: DocumentState) -> bool:
        return target in self.ALLOWED_TRANSITIONS.get(self.state, set())

    def transition_to(self, target: DocumentState, note: str = "") -> None:
        if not self.can_transition_to(target):
            raise InvalidStateTransitionError(self.state.value, target.value)
        self.history.append((self.state, note))
        self.state = target




@dataclass(frozen=True)
class GraphNode:
    """Bilgi çizgesindeki bir düğüm (örn. bir firma, bir proje)."""

    node_id: str
    label: str


@dataclass(frozen=True)
class GraphEdge:
    """
    Bilgi çizgesindeki yönlü bir kenar.

    `weight = -log(confidence)` — bkz. proje notları: Dijkstra bu ağırlığı
    minimize ettiğinde, aslında güven skorlarının ÇARPIMINI maksimize eder.
    """

    source_id: str
    target_id: str
    weight: float
    confidence: float


@dataclass(frozen=True)
class GraphPath:
    """Arama sonucu bulunan bir yol."""

    nodes: Tuple[str, ...]
    total_cost: float

    @property
    def probability(self) -> float:
        """Toplam maliyetten geri türetilen birleşik güven skoru."""
        return math.exp(-self.total_cost)


