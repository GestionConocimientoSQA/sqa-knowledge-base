"""Interfaces de persistencia (puertos hexagonales).

Cada `Protocol` define qué operaciones espera el dominio sobre una entidad
sin atarse a SQLAlchemy, asyncpg ni ningún detalle de stack. Los services
dependen de estos tipos; los adapters concretos los implementan.

Convención de ownership ([[project-security-idor-check]]):
- Toda operación sobre `Session`, `Document` (modificación), etc. recibe
  el `caller_oid` y el repositorio filtra por `owner_oid = caller_oid OR
  caller.is_admin = true`.
- Si el caller no tiene visibilidad sobre el recurso, el repo lanza
  `NotFoundError` (no `ForbiddenError` — no diferenciamos "no existe"
  vs "no podés verlo" para no filtrar existencia).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

from sqa_kb.domain.entities import (
    AuditLog,
    CaptureScore,
    Category,
    DocType,
    Document,
    DocumentChunk,
    DocumentDetail,
    HotTopic,
    IngestionItem,
    Message,
    MyCapturesStats,
    Project,
    ProjectCategory,
    ProjectDocType,
    ProjectMember,
    Query,
    QueryCitation,
    RecentActivityItem,
    Session,
    Skill,
    User,
)
from sqa_kb.domain.value_objects import (
    CategoryCode,
    DocStatus,
    DocTypeCode,
    IngestionStatus,
    SessionMode,
    SessionStatus,
)


@runtime_checkable
class ProjectRepository(Protocol):
    """Persistencia de proyectos + membresías (Fase 9.2).

    El servicio que orquesta esto (`ProjectService`) hace los checks de
    autorización ANTES de delegar — el repo no enforce permisos, solo
    expone CRUD limpio. La razón: las decisiones de quién puede ver/editar
    qué dependen del rol global + membership, y eso es lógica de servicio.
    """

    async def create(self, project: Project) -> Project: ...

    async def get(self, project_id: str) -> Project | None: ...

    async def get_by_slug(self, slug: str) -> Project | None: ...

    async def list_all(self) -> Sequence[Project]: ...
    """Lista todos los proyectos sin filtro (uso `gk_lead`)."""

    async def list_for_user(self, user_oid: str) -> Sequence[Project]: ...
    """Proyectos donde el usuario es miembro (cualquier rol)."""

    async def update(self, project: Project) -> Project: ...

    async def archive(self, project_id: str) -> Project: ...
    """Soft-delete: setea `archived_at = now()`. El proyecto queda
    read-only pero no se borra (queremos preservar el knowledge)."""

    # --- Memberships ---

    async def add_member(self, member: ProjectMember) -> ProjectMember: ...
    """Idempotente: si el `(project_id, user_oid)` ya existe, actualiza
    el `role` y devuelve la fila resultante."""

    async def remove_member(self, project_id: str, user_oid: str) -> None: ...
    """No-op si el miembro no existe."""

    async def list_members(self, project_id: str) -> Sequence[ProjectMember]: ...

    async def get_membership(
        self, project_id: str, user_oid: str
    ) -> ProjectMember | None: ...
    """Devuelve la membresía concreta del usuario en el proyecto.
    `None` si no es miembro. Usado por `PermissionPolicy` para construir
    el `ProjectMembership` derivado."""


@runtime_checkable
class ProjectTaxonomyRepository(Protocol):
    """Persistencia de overrides + extensiones de taxonomía por proyecto
    (Fase 9.4).

    El catálogo global vive en `TaxonomyRepository`. Este repo solo
    expone las modificaciones per-proyecto (delta sobre el global). El
    merge final lo orquesta `ProjectTaxonomyService.effective(...)`.
    """

    async def list_categories(self, project_id: str) -> Sequence[ProjectCategory]: ...

    async def list_doc_types(self, project_id: str) -> Sequence[ProjectDocType]: ...

    async def upsert_category(self, category: ProjectCategory) -> ProjectCategory: ...
    """Idempotente: si `(project_id, code)` ya existe, reemplaza label
    + is_override. El `project_owner` lo invoca para agregar override
    o extensión."""

    async def upsert_doc_type(self, doc_type: ProjectDocType) -> ProjectDocType: ...

    async def delete_category(self, project_id: str, code: str) -> None: ...
    """Elimina un override / extensión. Si era override (is_override=True)
    el global vuelve a estar vigente; si era extensión, desaparece."""

    async def delete_doc_type(self, project_id: str, code: str) -> None: ...


@runtime_checkable
class UserRepository(Protocol):
    """Espejo del catálogo de usuarios. La creación/actualización se hace
    desde el JWT de Entra ID (o el dev provider en local) — no hay un
    endpoint público para crear usuarios."""

    async def upsert_from_token(self, user: User) -> User: ...
    """Crea o actualiza un usuario a partir de los claims del JWT.
    Atómico — usado en el primer login y en cada token nuevo si cambió
    el role o las carpetas owned."""

    async def get_by_oid(self, oid: str) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...
    """Lookup por email — usado al designar `project_owner` de un proyecto
    nuevo (el GK Lead provee el email del invitado, no su OID)."""

    async def list_by_role(self, role: str, *, limit: int = 50) -> Sequence[User]: ...


@runtime_checkable
class SessionRepository(Protocol):
    """Repositorio de sesiones de chat con Aria.

    Todas las queries reciben `caller_oid` para enforcement de IDOR
    ([[project-security-idor-check]]) — incluso para admins, para que
    quede registrado en audit_log el acceso a sesiones ajenas.
    """

    async def create(self, session: Session) -> Session: ...

    async def get(self, session_id: str, *, caller_oid: str) -> Session | None: ...
    """`None` si no existe o el caller no tiene visibilidad."""

    async def list_for_user(
        self,
        caller_oid: str,
        *,
        mode: SessionMode | None = None,
        status: SessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Session]: ...

    async def update_status(
        self,
        session_id: str,
        status: SessionStatus,
        *,
        caller_oid: str,
    ) -> Session: ...
    """Pausa/reanuda. Lanza `NotFoundError` si no hay visibilidad."""

    async def delete(self, session_id: str, *, caller_oid: str) -> None: ...

    async def append_message(self, message: Message, *, caller_oid: str) -> Message: ...

    async def list_messages(
        self,
        session_id: str,
        *,
        caller_oid: str,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[Message]: ...


@runtime_checkable
class DocumentRepository(Protocol):
    """Catálogo del KB."""

    async def get(self, document_id: str) -> Document | None: ...

    async def get_detail(self, document_id: str) -> DocumentDetail | None: ...

    async def search(
        self,
        *,
        query: str | None = None,
        carpetas: Iterable[CategoryCode] | None = None,
        tipos: Iterable[DocTypeCode] | None = None,
        estados: Iterable[DocStatus] | None = None,
        autoritativo: bool | None = None,
        anonimizado: bool | None = None,
        min_score: float | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        author_oid: str | None = None,
        sort_by: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Document], int]: ...
    """Devuelve `(items, total)` para paginar. Espejo del `searchDocuments`
    del frontend (`apps/frontend/src/lib/api/documents.ts`)."""

    async def create(self, doc: Document) -> Document: ...

    async def update(self, doc: Document) -> Document: ...

    async def set_authoritative(
        self,
        document_id: str,
        *,
        value: bool,
        caller_oid: str,
    ) -> Document: ...

    async def list_by_author(
        self,
        author_oid: str,
        *,
        limit: int = 200,
    ) -> tuple[Sequence[Document], MyCapturesStats]: ...

    async def save_score(self, score: CaptureScore) -> CaptureScore: ...


@runtime_checkable
class ChunkRepository(Protocol):
    """Persistencia de chunks vectoriales (Fase 3 RAG).

    Operaciones mínimas:
    - `bulk_insert`: el indexer carga muchos chunks de una vez (un doc
      grande puede tener 50-100 chunks). Implementación PG usa
      `INSERT ... VALUES` multi-row para ahorrar round-trips.
    - `delete_by_document`: re-indexar requiere borrar chunks viejos
      antes de insertar los nuevos. La FK con `ON DELETE CASCADE`
      desde `documents` se encarga del cleanup automático al borrar el
      doc — esto es solo para re-index manual sin borrar el doc.
    - `count_for_document`: smoke check post-indexación.

    El retriever (Fase 3.3) NO usa este puerto — la query vector + boost
    se compone directamente sobre la tabla `document_chunks` con SQL
    crudo para aprovechar `pgvector` y el índice HNSW.
    """

    async def bulk_insert(self, chunks: Sequence[DocumentChunk]) -> int: ...
    """Inserta los chunks en una sola transacción. Devuelve cuántos
    se persistieron exitosamente."""

    async def delete_by_document(self, document_id: str) -> int: ...
    """Borra los chunks de un documento. Devuelve cuántos eliminó.
    Idempotente — si no hay chunks, devuelve 0."""

    async def count_for_document(self, document_id: str) -> int: ...
    """Cuántos chunks tiene un documento. Útil para validar pos-indexación."""


@runtime_checkable
class IngestionRepository(Protocol):
    """Bandeja de items pendientes de procesar (modo C)."""

    async def create(self, item: IngestionItem) -> IngestionItem: ...

    async def get(self, item_id: str) -> IngestionItem | None: ...

    async def list_pending(
        self, *, limit: int = 50, offset: int = 0
    ) -> Sequence[IngestionItem]: ...

    async def list_by_status(
        self,
        statuses: Iterable[IngestionStatus] | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[IngestionItem]: ...
    """Lista items filtrando por uno o más `status`. `None` = todos.
    Ordenados por `uploaded_at` desc. Espejo del `GET /ingestion`."""

    async def update(self, item: IngestionItem) -> IngestionItem: ...


@runtime_checkable
class QueryRepository(Protocol):
    """Consultas hechas al KB (modo B). Útil para hot topics y gap detection."""

    async def record(self, query: Query) -> Query: ...

    async def add_citation(self, citation: QueryCitation) -> QueryCitation: ...

    async def hot_topics(
        self, *, since_days: int = 30, limit: int = 8
    ) -> Sequence[HotTopic]: ...


@runtime_checkable
class TaxonomyRepository(Protocol):
    """Carpetas + tipos de documento. Lectura libre; escritura solo GK Lead."""

    async def list_categories(self) -> Sequence[Category]: ...

    async def list_doc_types(self) -> Sequence[DocType]: ...


@runtime_checkable
class SkillRepository(Protocol):
    """Skills (prompts) del agente. Edición desde admin (Fase 9)."""

    async def list_enabled(self) -> Sequence[Skill]: ...

    async def get(self, skill_id: str) -> Skill | None: ...

    async def upsert(self, skill: Skill) -> Skill: ...


@runtime_checkable
class AuditLogRepository(Protocol):
    """Log inmutable de eventos. Append-only — no hay update ni delete.

    Si TI define un audit log central en Azure SQL Serverless
    ([[docs/alineacion-arquitectura-ti.md §2.5]]), un adapter concreto
    puede escribir a ambos (local + central) sin que el caller se entere.
    """

    async def append(self, entry: AuditLog) -> AuditLog: ...

    async def list_for_resource(
        self,
        resource_id: str,
        *,
        limit: int = 100,
    ) -> Sequence[AuditLog]: ...


@runtime_checkable
class ActivityRepository(Protocol):
    """Feed de actividad reciente (dashboard frontend Fase 7)."""

    async def recent(
        self, *, limit: int = 12, since_iso: str | None = None
    ) -> Sequence[RecentActivityItem]: ...
