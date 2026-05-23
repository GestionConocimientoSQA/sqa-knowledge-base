"""Implementaciones de los `ports.repositories.*`.

Cada subpaquete implementa los Protocols para una tecnología concreta:
- `postgres/` — SQLAlchemy 2.0 async + asyncpg + pgvector. Default en
  desarrollo local y en producción si TI confirma PostgreSQL Flexible Server.
- `azure_sql/` — placeholder para el adapter mssql/aioodbc si TI decide
  Azure SQL Database (ver docs/alineacion-arquitectura-ti.md §2.2).
"""
