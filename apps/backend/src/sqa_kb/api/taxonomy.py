"""Endpoints de taxonomía — carpetas + tipos de documento.

Lectura abierta para cualquier usuario autenticado. Escritura solo GK Lead
desde el panel admin (Fase 9), no expuesta acá todavía.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter

from sqa_kb.api.dependencies import CurrentUser, TaxonomyRepoDep
from sqa_kb.domain.entities import Category, DocType

router = APIRouter(tags=["taxonomy"])


@router.get("/categories", response_model=list[Category])
async def list_categories(
    repo: TaxonomyRepoDep,
    _user: CurrentUser,
) -> Sequence[Category]:
    """Lista las 8 carpetas temáticas con sus stats agregados."""
    return await repo.list_categories()


@router.get("/doc-types", response_model=list[DocType])
async def list_doc_types(
    repo: TaxonomyRepoDep,
    _user: CurrentUser,
) -> Sequence[DocType]:
    """Lista los 11 tipos de documento del playbook SQA."""
    return await repo.list_doc_types()
