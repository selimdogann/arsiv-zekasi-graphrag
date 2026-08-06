"""
Uygulama ayarları — ortam değişkenlerinden (environment variables) okunur.

`DATABASE_URL` tanımlıysa kalıcı PostgreSQL adaptörleri, tanımlı değilse
bellek-içi (InMemory) adaptörler kullanılır. Böylece demo ve testler bir
veritabanı gerektirmeden çalışmaya devam eder; üretimde ise tek bir ortam
değişkeni kalıcılığı açar.

`API_KEY` tanımlıysa veri uçları API anahtarı ister. Tanımlı değilse
doğrulama KAPALIDIR (yerel geliştirme kolaylığı) — bu durum sağlık ucunda
`auth_enabled: false` olarak açıkça bildirilir.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# bge-m3 embedding boyutu. pgvector sütunu SABİT boyut ister; embedding modeli
# değişirse burası da güncellenmeli (ve tablo yeniden oluşturulmalı).
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    api_key: str | None
    embed_dim: int


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL"),
        # Boş dizeyi "tanımsız" say: API_KEY="" ile doğrulama açılmasın.
        api_key=os.getenv("API_KEY") or None,
        embed_dim=EMBED_DIM,
    )
