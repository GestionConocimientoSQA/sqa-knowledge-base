"""Ports — interfaces que el dominio espera del mundo externo.

Cada Protocol/abc en este módulo define un contrato (qué métodos, qué tipos
de entrada/salida) sin atarse a una implementación concreta.

- `repositories.py` — interfaces para persistencia (User, Session, Document...)
- `gateways.py` — interfaces para servicios externos (LLM, Blob, Email)

Las implementaciones concretas viven en `adapters/`. Esto permite:
- Tests con fakes/mocks sin levantar PostgreSQL ni LiteLLM
- Cambiar el stack de DB (PostgreSQL ↔ Azure SQL) sin tocar `services/`
- Swap del proveedor de LLM (Anthropic directo ↔ LiteLLM proxy) ídem
"""
