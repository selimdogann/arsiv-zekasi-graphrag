-- Postgres ilk açılışında çalışır: pgvector eklentisini etkinleştirir.
-- (Tabloları uygulama, SQLAlchemy ile kendisi oluşturur.)
CREATE EXTENSION IF NOT EXISTS vector;
