"""DocumentationSessionService — workflow guiado de captura del
conocimiento del cliente (Fase 9.5).

El `project_owner` (o `gk_lead`) abre una sesión, completa 5 steps con
preguntas estructuradas sobre el cliente del proyecto, y al finalizar
el servicio:

1. Compila las respuestas en markdown por step (uno por área).
2. Empuja cada `.md` al pipeline de ingesta del proyecto (modo C).
3. Marca la sesión `finalized` y guarda los IDs de los ingestion items
   generados.

A partir de ahí, el `project_owner` aprueba cada item con la cola de
ingesta estándar — heredan el `project_id` y la taxonomía efectiva del
proyecto. Es la "semilla" de conocimiento del proyecto.

Diseño:
- Workflow lineal (sin LangGraph). El state vive en `step_data` JSONB.
- Cada step tiene una forma de payload validada por Pydantic
  (`StepPayloadXxx`). El servicio rechaza payloads malformados.
- Las transiciones avanzan secuencialmente: no se puede saltar steps.
- `finalize` requiere que TODOS los steps hayan sido completados.

Autorización (espejo del ADR §D2):
- Abrir / completar / finalizar: `project_owner` o `gk_lead`.
- Listar / ver: cualquier miembro del proyecto.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from sqa_kb.domain.entities import DocumentationSession, User
from sqa_kb.domain.errors import ForbiddenError, NotFoundError, ValidationError
from sqa_kb.domain.value_objects import (
    DOCUMENTATION_STEP_ORDER,
    DocumentationSessionStatus,
    DocumentationStep,
)
from sqa_kb.ports.repositories import (
    DocumentationSessionRepository,
    ProjectRepository,
)
from sqa_kb.services.ingestion_service import IngestionService
from sqa_kb.services.project_service import PermissionPolicy


# ===========================================================================
# Payloads por step
# ===========================================================================
#
# Cada step tiene una "forma" estándar — el frontend envía el payload con
# alias camelCase y el servicio lo valida. Estas clases NO se persisten
# (Pydantic se usa solo para validar el dict que entra al `step_data`).


class _CamelBase(BaseModel):
    """Acepta camelCase y snake_case para evitar fricciones con el frontend."""

    model_config = {"populate_by_name": True}


class ContextPayload(_CamelBase):
    """Step 1 — Contexto del cliente."""

    industry: str = Field(min_length=1, max_length=255)
    regulation: str = Field(default="", max_length=2000)
    """Marco regulatorio si aplica (ej. 'BCRA Comm A 7724', 'HIPAA')."""
    initial_glossary: list[str] = Field(default_factory=list)
    """Términos iniciales que el cliente usa (se afinan en step 4)."""


class TaxonomyPayload(_CamelBase):
    """Step 2 — Taxonomía deseada."""

    category_extensions: list[str] = Field(default_factory=list)
    """Codes nuevos que el cliente quiere (ej. 'REG', 'CLI-FIN')."""
    doc_type_extensions: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=2000)


class SourcesPayload(_CamelBase):
    """Step 3 — Fuentes de información disponibles."""

    sources: list[str] = Field(default_factory=list)
    """URLs o descripciones (SharePoint, Drive, repos, wiki, etc.)."""
    access_notes: str = Field(default="", max_length=2000)


class GlossaryPayload(_CamelBase):
    """Step 4 — Glosario refinado."""

    terms: list[dict[str, str]] = Field(default_factory=list)
    """Lista de {term, definition, synonyms} para alimentar FTS."""


class StakeholdersPayload(_CamelBase):
    """Step 5 — Stakeholders y aprobadores."""

    stakeholders: list[dict[str, str]] = Field(default_factory=list)
    """Lista de {name, role, area, approves}."""


# Mapa step → clase Pydantic que valida el payload.
_STEP_VALIDATORS: dict[DocumentationStep, type[BaseModel]] = {
    DocumentationStep.CONTEXT: ContextPayload,
    DocumentationStep.TAXONOMY: TaxonomyPayload,
    DocumentationStep.SOURCES: SourcesPayload,
    DocumentationStep.GLOSSARY: GlossaryPayload,
    DocumentationStep.STAKEHOLDERS: StakeholdersPayload,
}


# ===========================================================================
# Service
# ===========================================================================


class DocumentationSessionService:
    """Orquesta el workflow de sesión de documentación."""

    def __init__(
        self,
        repo: DocumentationSessionRepository,
        project_repo: ProjectRepository,
        ingestion_service: IngestionService,
    ) -> None:
        self._repo = repo
        self._projects = project_repo
        self._ingestion = ingestion_service
        self._policy = PermissionPolicy(project_repo)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    async def _require_session(self, session_id: str) -> DocumentationSession:
        session = await self._repo.get(session_id)
        if session is None:
            raise NotFoundError(
                f"Sesión de documentación {session_id} no encontrada"
            )
        return session

    async def _require_edit(self, caller: User, project_id: str) -> None:
        project = await self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")
        membership = await self._policy.resolve(caller, project_id)
        # Reutilizamos `can_edit_taxonomy` — es el mismo gate (project_owner
        # o gk_lead). Una sesión de documentación es administración del
        # proyecto, equivalente a editar taxonomía o miembros.
        if not membership.can_edit_taxonomy:
            raise ForbiddenError(
                "Solo project_owner o gk_lead pueden conducir sesiones de "
                "documentación"
            )

    async def _require_read(self, caller: User, project_id: str) -> None:
        project = await self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")
        membership = await self._policy.resolve(caller, project_id)
        if not membership.can_read:
            raise NotFoundError(f"Proyecto {project_id} no encontrado")

    @staticmethod
    def _next_step(
        current: DocumentationStep | str,
    ) -> DocumentationStep | None:
        """Devuelve el siguiente step en el orden fijo. `None` si era el último.

        Acepta `str` o `DocumentationStep` porque al volver de DB el valor
        viene como string (use_enum_values=True en `_Base`)."""
        current_value = str(current)
        for i, step in enumerate(DOCUMENTATION_STEP_ORDER):
            if step.value == current_value:
                if i + 1 >= len(DOCUMENTATION_STEP_ORDER):
                    return None
                return DOCUMENTATION_STEP_ORDER[i + 1]
        return None

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def start(self, caller: User, project_id: str) -> DocumentationSession:
        """Abre una sesión nueva en step `context`."""
        await self._require_edit(caller, project_id)
        session = DocumentationSession(
            id=str(uuid.uuid4()),
            project_id=project_id,
            owner_oid=caller.oid,
            status=DocumentationSessionStatus.IN_PROGRESS,
            current_step=DocumentationStep.CONTEXT,
            step_data={},
            started_at=datetime.now(UTC),
        )
        return await self._repo.create(session)

    async def get(self, caller: User, session_id: str) -> DocumentationSession:
        session = await self._require_session(session_id)
        await self._require_read(caller, session.project_id)
        return session

    async def list_for_project(
        self, caller: User, project_id: str
    ) -> Sequence[DocumentationSession]:
        await self._require_read(caller, project_id)
        return await self._repo.list_for_project(project_id)

    async def submit_step(
        self,
        caller: User,
        session_id: str,
        step: DocumentationStep,
        payload: dict[str, Any],
    ) -> DocumentationSession:
        """Acepta el payload del step actual y avanza al siguiente.

        El step a enviar debe coincidir con `session.current_step` — no se
        permite reenviar steps anteriores ni saltar steps.
        """
        session = await self._require_session(session_id)
        await self._require_edit(caller, session.project_id)

        if session.status != DocumentationSessionStatus.IN_PROGRESS:
            raise ValidationError(
                "La sesión no está en progreso — no acepta más steps"
            )
        # `current_step` se almacena como string (use_enum_values=True en
        # _Base) — comparamos contra el valor del enum, no el enum mismo.
        if str(step) != str(session.current_step):
            raise ValidationError(
                f"Se esperaba el step {str(session.current_step)!r}; "
                f"recibido {str(step)!r}"
            )

        # Valida payload contra la forma esperada del step. `step` puede
        # venir como str (vía FastAPI path enum) o DocumentationStep —
        # normalizamos al enum para indexar `_STEP_VALIDATORS`.
        step_enum = (
            step
            if isinstance(step, DocumentationStep)
            else DocumentationStep(str(step))
        )
        validator = _STEP_VALIDATORS[step_enum]
        try:
            validated = validator.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(
                f"Payload inválido para step {step.value}: {exc}"
            ) from exc

        # Avanza al siguiente step (o queda en el último, pendiente de finalize).
        next_step = self._next_step(step_enum)
        new_step = next_step if next_step is not None else step_enum

        updated = session.model_copy(
            update={
                "step_data": {
                    **session.step_data,
                    step_enum.value: validated.model_dump(),
                },
                "current_step": new_step,
            }
        )
        return await self._repo.update(updated)

    async def finalize(
        self, caller: User, session_id: str
    ) -> DocumentationSession:
        """Compila las respuestas en docs `.md`, los envía al pipeline de
        ingesta del proyecto, marca la sesión `finalized`.

        Requiere que TODOS los steps tengan respuesta. Si falta alguno,
        lanza `ValidationError`.
        """
        session = await self._require_session(session_id)
        await self._require_edit(caller, session.project_id)

        if session.status != DocumentationSessionStatus.IN_PROGRESS:
            raise ValidationError(
                "La sesión ya fue finalizada o abandonada"
            )

        missing = [
            s.value
            for s in DOCUMENTATION_STEP_ORDER
            if s.value not in session.step_data
        ]
        if missing:
            raise ValidationError(
                f"Faltan steps por completar: {', '.join(missing)}"
            )

        # Genera un .md por step y lo manda a ingesta.
        generated_ids: list[str] = []
        for step in DOCUMENTATION_STEP_ORDER:
            md_bytes = self._render_step_markdown(session, step)
            filename = f"doc-session-{session.id[:8]}-{step.value}.md"
            item = await self._ingestion.upload(
                filename=filename,
                data=md_bytes,
                uploaded_by_oid=caller.oid,
                project_id=session.project_id,
                source_origin=f"documentation-session:{session.id}",
            )
            generated_ids.append(item.id)

        finalized = session.model_copy(
            update={
                "status": DocumentationSessionStatus.FINALIZED,
                "finalized_at": datetime.now(UTC),
                "generated_document_ids": generated_ids,
            }
        )
        return await self._repo.update(finalized)

    async def abandon(
        self, caller: User, session_id: str
    ) -> DocumentationSession:
        """Marca la sesión como abandonada (no genera docs)."""
        session = await self._require_session(session_id)
        await self._require_edit(caller, session.project_id)
        if session.status != DocumentationSessionStatus.IN_PROGRESS:
            raise ValidationError(
                "La sesión ya fue finalizada o abandonada"
            )
        abandoned = session.model_copy(
            update={"status": DocumentationSessionStatus.ABANDONED}
        )
        return await self._repo.update(abandoned)

    # -----------------------------------------------------------------------
    # Renderizado de markdown por step
    # -----------------------------------------------------------------------

    def _render_step_markdown(
        self, session: DocumentationSession, step: DocumentationStep
    ) -> bytes:
        """Renderiza el payload del step a markdown con frontmatter YAML.

        El `.md` resultante entra al pipeline de ingesta y luego el
        `project_owner` lo aprueba con trazabilidad estándar — heredando
        el `project_id` y la taxonomía efectiva del proyecto.
        """
        data = session.step_data.get(step.value, {})
        title = _STEP_TITLES[step]
        sections = _render_sections_for_step(step, data)
        body = "\n\n".join(sections)
        # Frontmatter YAML simple (sin librería) — fácil de parsear por el
        # extractor y útil como metadata.
        frontmatter = (
            "---\n"
            f"session_id: {session.id}\n"
            f"project_id: {session.project_id}\n"
            f"step: {step.value}\n"
            f"title: {title}\n"
            "---\n\n"
        )
        full = f"{frontmatter}# {title}\n\n{body}\n"
        return full.encode("utf-8")


# ===========================================================================
# Renderizado helpers (puros — fácil de testear)
# ===========================================================================


_STEP_TITLES: dict[DocumentationStep, str] = {
    DocumentationStep.CONTEXT: "Contexto del cliente",
    DocumentationStep.TAXONOMY: "Taxonomía del proyecto",
    DocumentationStep.SOURCES: "Fuentes de información",
    DocumentationStep.GLOSSARY: "Glosario del cliente",
    DocumentationStep.STAKEHOLDERS: "Stakeholders y aprobadores",
}


def _render_sections_for_step(
    step: DocumentationStep, data: dict[str, Any]
) -> list[str]:
    """Renderiza el cuerpo markdown por step. Funciones puras, testeables.

    No se preocupa por la cabecera — `MarkdownGenerator` la pone."""
    if step == DocumentationStep.CONTEXT:
        return _render_context(data)
    if step == DocumentationStep.TAXONOMY:
        return _render_taxonomy(data)
    if step == DocumentationStep.SOURCES:
        return _render_sources(data)
    if step == DocumentationStep.GLOSSARY:
        return _render_glossary(data)
    if step == DocumentationStep.STAKEHOLDERS:
        return _render_stakeholders(data)
    return []


def _render_context(data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    out.append(f"## Industria\n\n{data.get('industry', '—')}")
    if data.get("regulation"):
        out.append(f"## Marco regulatorio\n\n{data['regulation']}")
    glossary = data.get("initial_glossary") or data.get("initialGlossary") or []
    if glossary:
        out.append(
            "## Glosario inicial\n\n"
            + "\n".join(f"- {term}" for term in glossary)
        )
    return out


def _render_taxonomy(data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    cat = data.get("category_extensions") or data.get("categoryExtensions") or []
    tip = data.get("doc_type_extensions") or data.get("docTypeExtensions") or []
    if cat:
        out.append(
            "## Categorías nuevas\n\n"
            + "\n".join(f"- `{c}`" for c in cat)
        )
    if tip:
        out.append(
            "## Tipos de documento nuevos\n\n"
            + "\n".join(f"- `{t}`" for t in tip)
        )
    notes = data.get("notes")
    if notes:
        out.append(f"## Notas\n\n{notes}")
    return out or ["## Taxonomía\n\nSin extensiones — usa el catálogo global."]


def _render_sources(data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    sources = data.get("sources") or []
    if sources:
        out.append(
            "## Fuentes\n\n"
            + "\n".join(f"- {s}" for s in sources)
        )
    notes = data.get("access_notes") or data.get("accessNotes")
    if notes:
        out.append(f"## Notas de acceso\n\n{notes}")
    return out or ["## Fuentes\n\n(sin fuentes declaradas)"]


def _render_glossary(data: dict[str, Any]) -> list[str]:
    terms = data.get("terms") or []
    if not terms:
        return ["## Glosario\n\n(vacío)"]
    lines = ["## Glosario\n"]
    for term in terms:
        name = term.get("term", "—")
        definition = term.get("definition", "")
        synonyms = term.get("synonyms", "")
        lines.append(f"### {name}\n\n{definition}")
        if synonyms:
            lines.append(f"**Sinónimos:** {synonyms}")
    return ["\n\n".join(lines)]


def _render_stakeholders(data: dict[str, Any]) -> list[str]:
    stakeholders = data.get("stakeholders") or []
    if not stakeholders:
        return ["## Stakeholders\n\n(sin definir)"]
    lines = ["## Stakeholders\n"]
    lines.append("| Nombre | Rol | Área | Aprueba |")
    lines.append("|---|---|---|---|")
    for s in stakeholders:
        lines.append(
            f"| {s.get('name', '—')} | {s.get('role', '—')} | "
            f"{s.get('area', '—')} | {s.get('approves', '—')} |"
        )
    return ["\n".join(lines)]
