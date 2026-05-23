"""Seed inicial — taxonomía + usuarios stub.

Carga:
- 8 categorías (PROC, TEC, ARQ, HERR, NEG, ENV, EST, CONT) con counts
  iniciales que matchean los mocks del frontend (`lib/mocks/data.ts`).
- 11 tipos de documento (POL, PROC, GUIA, ...).
- 3 usuarios stub que el dev auth provider (1B.3) reconoce — espejo de
  los oids del frontend (`AUTHOR_OIDS` en `lib/mocks/data.ts`).

Uso desde CLI:
    python -m sqa_kb.adapters.repositories.postgres.seed

Idempotente: usa `ON CONFLICT DO NOTHING` para que correrlo dos veces
no falle.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from sqa_kb.adapters.repositories.postgres import models
from sqa_kb.adapters.repositories.postgres.session import (
    create_engine,
    create_session_factory,
    session_scope,
)
from sqa_kb.config import get_settings

# Espejo de FOLDERS en frontend mocks (lib/mocks/data.ts).
CATEGORIES: list[dict[str, object]] = [
    {"code": "PROC", "label": "Procesos", "docs": 84, "vigentes": 76, "autoritativos": 41, "score_avg": 3.8, "obsolescencia": 4},
    {"code": "TEC", "label": "Técnico", "docs": 142, "vigentes": 128, "autoritativos": 88, "score_avg": 4.1, "obsolescencia": 6},
    {"code": "ARQ", "label": "Arquitectura", "docs": 47, "vigentes": 44, "autoritativos": 38, "score_avg": 4.4, "obsolescencia": 1},
    {"code": "HERR", "label": "Herramientas", "docs": 96, "vigentes": 81, "autoritativos": 52, "score_avg": 3.6, "obsolescencia": 9},
    {"code": "NEG", "label": "Negocio", "docs": 38, "vigentes": 35, "autoritativos": 28, "score_avg": 3.9, "obsolescencia": 2},
    {"code": "ENV", "label": "Ambientes", "docs": 29, "vigentes": 24, "autoritativos": 17, "score_avg": 3.5, "obsolescencia": 3},
    {"code": "EST", "label": "Estándares", "docs": 22, "vigentes": 22, "autoritativos": 22, "score_avg": 4.6, "obsolescencia": 0},
    {"code": "CONT", "label": "Contexto", "docs": 18, "vigentes": 15, "autoritativos": 9, "score_avg": 3.4, "obsolescencia": 2},
]

DOC_TYPES: list[dict[str, str]] = [
    {"code": "POL", "label": "Política"},
    {"code": "PROC", "label": "Procedimiento"},
    {"code": "GUIA", "label": "Guía"},
    {"code": "INST", "label": "Instructivo"},
    {"code": "SERV", "label": "Servicio"},
    {"code": "MTEC", "label": "Memoria técnica"},
    {"code": "ACEL", "label": "Acelerador"},
    {"code": "UEN", "label": "UEN"},
    {"code": "ARCL", "label": "Arquetipo cliente"},
    {"code": "FORM", "label": "Formato"},
    {"code": "PRES", "label": "Presentación"},
]

# 3 usuarios stub — mismos OIDs que el dev provider Fase 1B.3 emite cuando
# el frontend pide login con cada rol. Los `carpetas_owned` los seteamos
# para que Owner sea admin sobre TEC + ARQ (caso típico).
USERS: list[dict[str, object]] = [
    {
        "oid": "stub-capturador-00000000",
        "email": "lucia.vargas@sqa.co",
        "name": "Lucía Vargas",
        "role_id": "capturador",
        "carpetas_owned": [],
        "puede_gobernar_taxonomia": False,
        "puede_aprobar_taxonomia": False,
        "puede_ver_metricas_globales": False,
    },
    {
        "oid": "stub-owner-00000000",
        "email": "camila.pereyra@sqa.co",
        "name": "Camila Pereyra",
        "role_id": "owner",
        "carpetas_owned": ["TEC", "ARQ"],
        "puede_gobernar_taxonomia": False,
        "puede_aprobar_taxonomia": False,
        "puede_ver_metricas_globales": True,
    },
    {
        "oid": "stub-gklead-00000000",
        "email": "andres.altamiranda@sqa.co",
        "name": "Andrés Altamiranda",
        "role_id": "gklead",
        "carpetas_owned": [],
        "puede_gobernar_taxonomia": True,
        "puede_aprobar_taxonomia": True,
        "puede_ver_metricas_globales": True,
    },
]


async def seed(session_factory: async_sessionmaker) -> dict[str, int]:
    """Inserta los datos base. Devuelve `{categories, doc_types, users}` con
    el conteo de rows existentes después del seed."""
    async with session_scope(session_factory) as db:
        # Categories
        if CATEGORIES:
            stmt = pg_insert(models.CategoryModel).values(CATEGORIES)
            stmt = stmt.on_conflict_do_nothing(index_elements=["code"])
            await db.execute(stmt)

        # Doc types
        if DOC_TYPES:
            stmt = pg_insert(models.DocTypeModel).values(DOC_TYPES)
            stmt = stmt.on_conflict_do_nothing(index_elements=["code"])
            await db.execute(stmt)

        # Users
        if USERS:
            stmt = pg_insert(models.UserModel).values(USERS)
            stmt = stmt.on_conflict_do_nothing(index_elements=["oid"])
            await db.execute(stmt)

    # Counts post-seed (separada para no mezclar con commit del scope anterior).
    async with session_factory() as db:
        from sqlalchemy import func, select

        cats = (
            await db.execute(select(func.count()).select_from(models.CategoryModel))
        ).scalar_one()
        dts = (
            await db.execute(select(func.count()).select_from(models.DocTypeModel))
        ).scalar_one()
        usrs = (
            await db.execute(select(func.count()).select_from(models.UserModel))
        ).scalar_one()
        return {"categories": cats, "doc_types": dts, "users": usrs}


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        counts = await seed(factory)
        print(
            f"[seed] categories={counts['categories']} "
            f"doc_types={counts['doc_types']} users={counts['users']}"
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
