"""
Ports (Abstract Base Class'lar) — Clean Architecture'ın "sınır" katmanı.

Bu ABC'ler, sistemin dış dünyadan ne İSTEDİĞİNİ tanımlar; NASIL sağlandığını
değil. Somut altyapı (bir dosya okuyucu, bir PDF ayrıştırıcı, bir LLM istemcisi)
bu sözleşmeleri UYGULAR. Domain, hangi somut teknolojinin kullanıldığını
asla bilmez — bu, düşük bağımlılığın (low coupling) temelidir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List,Tuple


from graphrag.domain.entities import (
    Chunk,
    Document,
    DocumentInfo,
    GraphEdge,
    GraphNode,
)
from graphrag.domain.privacy import AuditEvent


class IDocumentLoader(ABC):
    """Ham bir kaynağı (dosya, URL, ...) bir `Document`'a çeviren sözleşme."""

    @abstractmethod
    def load(self, uri: str) -> Document:
        """Verilen kaynaktan bir Document oluşturur."""


class IDocumentCatalog(ABC):
    """Arşive alınan belgelerin kaydı (ad, durum, zaman).

    Parçalar ve graf kalıcı olsa bile belge ADI kaybolursa arayüzdeki liste
    boşalır ve kaynak gösteriminde belge adı görünmez. Bu port, kaydı da
    kalıcı hâle getirilebilir kılar.
    """

    @abstractmethod
    def add(self, info: DocumentInfo) -> None:
        """Belge kaydını ekler (aynı id tekrar gelirse günceller)."""

    @abstractmethod
    def all(self) -> List[DocumentInfo]:
        """Tüm belge kayıtlarını, en yeniden eskiye döndürür."""


class IChunker(ABC):
    """Uzun bir metni, ayrı ayrı embed'lenecek küçük parçalara bölen sözleşme."""

    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """Metni parça (chunk) listesine böler. Boş metin için boş liste döner."""


class IGraphStore(ABC):
    """Bilgi çizgesi depolama sözleşmesi."""

    @abstractmethod
    def upsert_node(self, node: GraphNode) -> None:
        """Düğümü ekler/günceller."""

    @abstractmethod
    def upsert_edge(self, edge: GraphEdge) -> None:
        """Kenarı ekler/günceller."""

    @abstractmethod
    def neighbors(self, node_id: str) -> List[GraphEdge]:
        """Verilen düğümden ÇIKAN tüm kenarları döndürür (komşuluk listesi)."""
    
    @abstractmethod
    def get_node(self, node_id: str) -> GraphNode:
        """Verilen id'ye sahip düğümü döndürür."""

    @abstractmethod
    def all_nodes(self) -> List[GraphNode]:
        """Graftaki tüm düğümleri döndürür (varlık gezgini / istatistik için)."""

    @abstractmethod
    def edge_count(self) -> int:
        """Graftaki toplam kenar sayısı (istatistik için)."""



class IVectorStore(ABC):
    """Vektör benzerliği araması sözleşmesi."""

    @abstractmethod
    def upsert(self, chunks: List[Chunk]) -> None:
        """Chunk'ları depoya ekler/günceller."""

    @abstractmethod
    def search(self, query_embedding: Tuple[float, ...], top_k: int
               ) -> List["tuple[Chunk, float]"]:
        """En benzer top_k chunk'ı, (chunk, benzerlik_skoru) çiftleri olarak döndürür."""

    @abstractmethod
    def count(self) -> int:
        """Depodaki toplam parça (chunk) sayısı — istatistik için."""

    @abstractmethod
    def all_chunks(self) -> List[Chunk]:
        """Depodaki tüm parçalar. Kalıcı depodan bellek-içi anahtar kelime
        indeksini yeniden kurmak (uygulama açılışı) için gerekir."""


class IKeywordIndex(ABC):
    """Anahtar kelime (BM25) araması sözleşmesi — vektör aramanın 'lexical' eşi.

    Vektör araması ANLAM'a bakar; bu ise birebir KELİME eşleşmesine bakar.
    İkisi melez (hybrid) kullanıldığında hem eş anlamlılar hem tam terimler yakalanır.
    """

    @abstractmethod
    def index(self, chunks: List[Chunk]) -> None:
        """Chunk'ları anahtar-kelime indeksine ekler."""

    @abstractmethod
    def search(self, query: str, top_k: int) -> List["tuple[Chunk, float]"]:
        """Sorguyla en çok kelime örtüşen top_k chunk'ı (chunk, skor) olarak döndürür."""


class ILanguageModel(ABC):
    """LLM (dil modeli) çıkarım sözleşmesi."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Verilen prompt'un devamını (LLM'in ürettiği metni) döndürür."""
    
    @abstractmethod
    def embed(self, text: str) -> "tuple[float, ...]":
        """Metni bir embedding vektörüne (sayı dizisine) çevirir."""


class IEntityExtractor(ABC):
    """Metinden varlık (özel isim) adayları çıkaran sözleşme."""

    @abstractmethod
    def extract(self, text: str) -> List[str]:
        """Metindeki varlık adı adaylarını döndürür."""


class IAuditLog(ABC):
    """KVKK denetim kaydı sözleşmesi (append-only)."""

    @abstractmethod
    def record(self, event: AuditEvent) -> None:
        """Bir denetim olayını kalıcı olarak kaydeder."""

    @abstractmethod
    def events(self) -> List[AuditEvent]:
        """Kaydedilmiş denetim olaylarını döndürür (KVKK denetim raporu için)."""


class IPrivacyFilter(ABC):
    """KVKK kişisel veri (PII) maskeleme sözleşmesi."""

    @abstractmethod
    def redact(self, text: str) -> str:
        """Metindeki kişisel verileri kararlı takma adlarla değiştirir."""


class ICache(ABC):
    """Basit anahtar-değer önbellek sözleşmesi (memoization için)."""

    @abstractmethod
    def get(self, key: str):
        """Anahtara karşılık gelen değeri döndürür; önbellekte yoksa None."""

    @abstractmethod
    def set(self, key: str, value) -> None:
        """Anahtar-değer çiftini önbelleğe kaydeder."""
