-- ============================================================
-- SQA Knowledge Base — Initial DB setup
-- Ejecutado automáticamente por el contenedor pgvector la primera vez.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Las tablas del dominio las crea Alembic (Fase 1).
-- Acá solo dejamos las extensiones listas.
