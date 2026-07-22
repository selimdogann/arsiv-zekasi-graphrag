"""
Domain katmanı hata hiyerarşisi.

Tüm özel istisnalar tek bir kök (`GraphRAGError`) altında toplanır. Böylece
üst katmanlar tek bir `except GraphRAGError` ile projenin tüm hatalarını
yakalayabilir; alt katmanlar ise daha spesifik yakalama yapabilir.
"""
from __future__ import annotations


class GraphRAGError(Exception):
    """Sistemdeki tüm alan-özel istisnaların kök sınıfı."""


class InvalidStateTransitionError(GraphRAGError):
    """Deterministik durum makinesinde izin verilmeyen bir geçiş denendi."""

    def __init__(self, current: str, attempted: str) -> None:
        self.current = current
        self.attempted = attempted
        super().__init__(
            f"Geçersiz durum geçişi: '{current}' -> '{attempted}'."
        )


class IngestionError(GraphRAGError):
    """Doküman alma/okuma sürecinde oluşan hata (örn. dosya bulunamadı)."""


class PathNotFoundError(GraphRAGError):
    """İki düğüm arasında (verilen kısıtlar içinde) yol bulunamadı."""
