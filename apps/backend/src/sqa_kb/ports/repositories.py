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
    DocumentDetail,
    HotTopic,
    IngestionItem,
    Message,
    MyCapturesStats,
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
    SessionMode,
    SessionStatus,
)


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
class IngestionRepository(Protocol):
    """Bandeja de items pendientes de procesar (modo C)."""

    async def create(self, item: IngestionItem) -> IngestionItem: ...

    async def get(self, item_id: str) -> IngestionItem | None: ...

    async def list_pending(
        self, *, limit: int = 50, offset: int = 0
    ) -> Sequence[IngestionItem]: ...

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
