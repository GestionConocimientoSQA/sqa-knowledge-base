"""Endpoints de taxonomía por proyecto (Fase 9.4).

    GET    /projects/{id}/taxonomy                Vista efectiva (global + overrides)
    GET    /projects/{id}/taxonomy/overrides      Solo los overrides/extensiones
    PUT    /projects/{id}/taxonomy/categories/{code}     Upsert override/extensión carpeta
    PUT    /projects/{id}/taxonomy/doc-types/{code}      Upsert override/extensión tipo
    DELETE /projects/{id}/taxonomy/categories/{code}
    DELETE /projects/{id}/taxonomy/doc-types/{code}

Thin wrapper sobre `ProjectTaxonomyService`. La autorización vive en el
servicio (PermissionPolicy).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from sqa_kb.api.dependencies import (
    CurrentUser,
    ProjectTaxonomyServiceDep,
)
from sqa_kb.domain.entities import (
    EffectiveTaxonomy,
    ProjectCategory,
    ProjectDocType,
)
from sqa_kb.services.project_taxonomy_service import (
    CategoryInput,
    DocTypeInput,
)

router = APIRouter(tags=["project-taxonomy"], prefix="/projects/{project_id}/taxonomy")


# ===========================================================================
# Schemas
# ===========================================================================


class _CamelBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UpsertCategoryBody(_CamelBase):
    label: str = Field(min_length=1, max_length=255)
    parent_global_code: str | None = Field(default=None, max_length=16)
    is_override: bool = False
    """True ⇒ reemplaza label de un código global existente.
    False ⇒ extensión: agrega un código nuevo exclusivo del proyecto."""


class UpsertDocTypeBody(_CamelBase):
    label: str = Field(min_length=1, max_length=255)
    parent_global_code: str | None = Field(default=None, max_length=16)
    is_override: bool = False


class OverridesResponse(_CamelBase):
    project_id: str
    categories: list[ProjectCategory]
    doc_types: list[ProjectDocType]


# ===========================================================================
# Endpoints
# ===========================================================================


@router.get("", response_model=EffectiveTaxonomy)
async def get_effective_taxonomy(
    project_id: str,
    service: ProjectTaxonomyServiceDep,
    user: CurrentUser,
) -> EffectiveTaxonomy:
    """Vista efectiva del proyecto = global ∪ overrides + extensiones."""
    return await service.effective(user, project_id)


@router.get("/overrides", response_model=OverridesResponse)
async def list_overrides(
    project_id: str,
    service: ProjectTaxonomyServiceDep,
    user: CurrentUser,
) -> OverridesResponse:
    """Lista solo los overrides/extensiones del proyecto (sin merge).
    Útil para la UI de administración del `project_owner`."""
    cats, types = await service.list_project_overrides(user, project_id)
    return OverridesResponse(
        project_id=project_id,
        categories=list(cats),
        doc_types=list(types),
    )


@router.put(
    "/categories/{code}", response_model=ProjectCategory, status_code=200
)
async def upsert_category(
    project_id: str,
    code: str,
    body: UpsertCategoryBody,
    service: ProjectTaxonomyServiceDep,
    user: CurrentUser,
) -> ProjectCategory:
    return await service.upsert_category(
        user,
        project_id,
        CategoryInput(
            code=code,
            label=body.label,
            parent_global_code=body.parent_global_code,
            is_override=body.is_override,
        ),
    )


@router.put(
    "/doc-types/{code}", response_model=ProjectDocType, status_code=200
)
async def upsert_doc_type(
    project_id: str,
    code: str,
    body: UpsertDocTypeBody,
    service: ProjectTaxonomyServiceDep,
    user: CurrentUser,
) -> ProjectDocType:
    return await service.upsert_doc_type(
        user,
        project_id,
        DocTypeInput(
            code=code,
            label=body.label,
            parent_global_code=body.parent_global_code,
            is_override=body.is_override,
        ),
    )


@router.delete("/categories/{code}", status_code=204)
async def delete_category(
    project_id: str,
    code: str,
    service: ProjectTaxonomyServiceDep,
    user: CurrentUser,
) -> None:
    await service.delete_category(user, project_id, code)


@router.delete("/doc-types/{code}", status_code=204)
async def delete_doc_type(
    project_id: str,
    code: str,
    service: ProjectTaxonomyServiceDep,
    user: CurrentUser,
) -> None:
    await service.delete_doc_type(user, project_id, code)
