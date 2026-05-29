"""ProjectTaxonomyService — taxonomía efectiva por proyecto (Fase 9.4).

El catálogo final que ve un proyecto = global ∪ (overrides + extensiones
del proyecto). Esta es la única clase que conoce la regla de resolución:
los consumidores (classifier del agente, endpoint que sirve al frontend,
tests) piden la vista efectiva y no se preocupan por la fuente.

Reglas (ADR 0009 §D4):

1. Empezamos con el catálogo global completo.
2. Aplicamos overrides: si `(project_id, code)` existe con
   `is_override=True` y el `code` coincide con uno global, se reemplaza
   el `label`.
3. Añadimos extensiones: filas con `code` que no existe en el global —
   se añaden como nuevas entradas al catálogo efectivo.

Si un proyecto no tiene ningún override ni extensión, su taxonomía
efectiva es idéntica al global.

Autorización:
- Lectura del efectivo: cualquier miembro del proyecto o `gk_lead`.
- Mutaciones (upsert / delete): `project_owner` o `gk_lead`.

Las mutaciones validan ANTES de tocar el repo — el `PermissionPolicy`
es el único lugar donde se decide quién puede.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqa_kb.domain.entities import (
    Category,
    DocType,
    EffectiveCategoryEntry,
    EffectiveDocTypeEntry,
    EffectiveTaxonomy,
    ProjectCategory,
    ProjectDocType,
    User,
)
from sqa_kb.domain.errors import ForbiddenError, NotFoundError, ValidationError
from sqa_kb.ports.repositories import (
    ProjectRepository,
    ProjectTaxonomyRepository,
    TaxonomyRepository,
)
from sqa_kb.services.project_service import PermissionPolicy


@dataclass(frozen=True, slots=True)
class CategoryInput:
    """Inputs para `PUT /projects/{id}/taxonomy/categories/{code}`."""

    code: str
    label: str
    parent_global_code: str | None = None
    is_override: bool = False


@dataclass(frozen=True, slots=True)
class DocTypeInput:
    """Inputs para `PUT /projects/{id}/taxonomy/doc-types/{code}`."""

    code: str
    label: str
    parent_global_code: str | None = None
    is_override: bool = False


class ProjectTaxonomyService:
    """Resuelve y administra taxonomía por proyecto."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        taxonomy_repo: TaxonomyRepository,
        project_taxonomy_repo: ProjectTaxonomyRepository,
    ) -> None:
        self._projects = project_repo
        self._global_taxonomy = taxonomy_repo
        self._project_taxonomy = project_taxonomy_repo
        self._policy = PermissionPolicy(project_repo)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    async def _require_project_exists(self, project_id: str) -> None:
        project = await self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")

    async def _require_read_access(self, caller: User, project_id: str) -> None:
        await self._require_project_exists(project_id)
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_read:
            # Mismo 404 que el resto del servicio — no filtramos existencia.
            raise NotFoundError(f"Proyecto {project_id} no encontrado")

    async def _require_edit_access(self, caller: User, project_id: str) -> None:
        await self._require_project_exists(project_id)
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_edit_taxonomy:
            raise ForbiddenError(
                "Solo project_owner o gk_lead pueden editar la taxonomía del proyecto"
            )

    @staticmethod
    def _merge_categories(
        globals_: Sequence[Category],
        overrides: Sequence[ProjectCategory],
    ) -> list[EffectiveCategoryEntry]:
        """Implementa la regla de resolución para carpetas."""
        # Index por code para lookup O(1). Convertimos cada Category global
        # a su EffectiveCategoryEntry equivalente — preserva counters.
        by_code: dict[str, EffectiveCategoryEntry] = {
            c.code: EffectiveCategoryEntry(
                code=c.code,
                label=c.label,
                docs=c.docs,
                vigentes=c.vigentes,
                autoritativos=c.autoritativos,
                score_avg=c.score_avg,
                obsolescencia=c.obsolescencia,
                is_project_extension=False,
            )
            for c in globals_
        }
        for override in overrides:
            if override.is_override and override.code in by_code:
                # Reemplazo de label conservando los counters del global.
                existing = by_code[override.code]
                by_code[override.code] = existing.model_copy(
                    update={"label": override.label}
                )
            elif not override.is_override and override.code not in by_code:
                # Extensión: nueva carpeta exclusiva del proyecto. Sus
                # counters arrancan en 0 — el cron de taxonomía global
                # no la cuenta porque vive en `project_categories`.
                by_code[override.code] = EffectiveCategoryEntry(
                    code=override.code,
                    label=override.label,
                    is_project_extension=True,
                )
            # Si is_override=True pero el code no existe en global → ignorar
            # (es un override apuntando a nada). Si is_override=False pero
            # el code SÍ existe → ignorar (para customizar global hay que
            # usar is_override=True). Ambos casos son inputs inválidos
            # tolerados (no rompemos la consulta).
        return sorted(by_code.values(), key=lambda c: c.code)

    @staticmethod
    def _merge_doc_types(
        globals_: Sequence[DocType],
        overrides: Sequence[ProjectDocType],
    ) -> list[EffectiveDocTypeEntry]:
        by_code: dict[str, EffectiveDocTypeEntry] = {
            d.code: EffectiveDocTypeEntry(
                code=d.code, label=d.label, is_project_extension=False
            )
            for d in globals_
        }
        for override in overrides:
            if override.is_override and override.code in by_code:
                existing = by_code[override.code]
                by_code[override.code] = existing.model_copy(
                    update={"label": override.label}
                )
            elif not override.is_override and override.code not in by_code:
                by_code[override.code] = EffectiveDocTypeEntry(
                    code=override.code,
                    label=override.label,
                    is_project_extension=True,
                )
        return sorted(by_code.values(), key=lambda d: d.code)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def effective(
        self, caller: User, project_id: str
    ) -> EffectiveTaxonomy:
        """Devuelve la taxonomía efectiva del proyecto.

        Requiere `can_read` sobre el proyecto. Resuelve global ∪ overrides
        + extensiones.
        """
        await self._require_read_access(caller, project_id)

        globals_cats = await self._global_taxonomy.list_categories()
        globals_types = await self._global_taxonomy.list_doc_types()
        proj_cats = await self._project_taxonomy.list_categories(project_id)
        proj_types = await self._project_taxonomy.list_doc_types(project_id)

        return EffectiveTaxonomy(
            project_id=project_id,
            categories=self._merge_categories(globals_cats, proj_cats),
            doc_types=self._merge_doc_types(globals_types, proj_types),
        )

    async def list_project_overrides(
        self, caller: User, project_id: str
    ) -> tuple[Sequence[ProjectCategory], Sequence[ProjectDocType]]:
        """Lista solo los overrides/extensiones del proyecto (sin merge).

        Útil para la UI de administración: mostrarle al `project_owner`
        qué tiene customizado en este proyecto.
        """
        await self._require_read_access(caller, project_id)
        cats = await self._project_taxonomy.list_categories(project_id)
        types = await self._project_taxonomy.list_doc_types(project_id)
        return cats, types

    async def upsert_category(
        self, caller: User, project_id: str, payload: CategoryInput
    ) -> ProjectCategory:
        """Crea / actualiza un override o extensión de carpeta."""
        await self._require_edit_access(caller, project_id)
        if not payload.code.strip():
            raise ValidationError("El código de carpeta no puede estar vacío")
        if not payload.label.strip():
            raise ValidationError("El label de carpeta no puede estar vacío")
        return await self._project_taxonomy.upsert_category(
            ProjectCategory(
                project_id=project_id,
                code=payload.code,
                label=payload.label,
                parent_global_code=payload.parent_global_code,
                is_override=payload.is_override,
            )
        )

    async def upsert_doc_type(
        self, caller: User, project_id: str, payload: DocTypeInput
    ) -> ProjectDocType:
        await self._require_edit_access(caller, project_id)
        if not payload.code.strip():
            raise ValidationError("El código de tipo no puede estar vacío")
        if not payload.label.strip():
            raise ValidationError("El label de tipo no puede estar vacío")
        return await self._project_taxonomy.upsert_doc_type(
            ProjectDocType(
                project_id=project_id,
                code=payload.code,
                label=payload.label,
                parent_global_code=payload.parent_global_code,
                is_override=payload.is_override,
            )
        )

    async def delete_category(
        self, caller: User, project_id: str, code: str
    ) -> None:
        await self._require_edit_access(caller, project_id)
        await self._project_taxonomy.delete_category(project_id, code)

    async def delete_doc_type(
        self, caller: User, project_id: str, code: str
    ) -> None:
        await self._require_edit_access(caller, project_id)
        await self._project_taxonomy.delete_doc_type(project_id, code)
