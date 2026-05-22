"""Adapters — implementaciones concretas de los ports.

Cada subpaquete implementa uno o varios ports contra una tecnología real:
- `adapters/repositories/` — SQLAlchemy/asyncpg/aioodbc según stack final
- `adapters/llm/` — cliente Anthropic directo o LiteLLM proxy
- `adapters/blob/` — Azure Blob Storage (azure-storage-blob)
- `adapters/observability/` — structlog/OpenTelemetry/Langfuse/App Insights

En Fase 1A esta capa está casi vacía — las implementaciones reales llegan
en 1B (cuando TI confirme el stack de DB y el método de auth) y en Fase 2
(LLM gateway).
"""
