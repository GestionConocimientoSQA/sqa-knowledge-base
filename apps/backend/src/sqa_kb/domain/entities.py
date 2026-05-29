"""Entidades del dominio.

Espejo de §7 del `ROADMAP-IMPLEMENTACION-SQA-KB.md` y de los tipos del
frontend (`apps/frontend/src/types/domain.ts` y `types/agent.ts`).

Las entidades son **Pydantic v2 BaseModel** — sirven para:
- Validación de inputs (deserialización de JSON / form data)
- Serialización a JSON para la API
- Documentación automática en `/docs` (OpenAPI)

No tienen lógica de persistencia (eso vive en `adapters/repositories/`).
No tienen métodos HTTP (eso vive en `api/`). Sólo el modelo de datos +
reglas de validación expresables como Pydantic constraints.

Convención de campos:
- `id` siempre es UUID4 string (no int).
- Timestamps en ISO 8601 UTC. Modelados como `datetime` aware.
- `*_oid` = Microsoft Entra Object ID del usuario relacionado.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)
from pydantic.alias_generators import to_camel

from sqa_kb.domain.value_objects import (
    ActivityType,
    CategoryCode,
    DocStatus,
    DocTypeCode,
    IngestionStatus,
    MessageRole,
    MessageStatus,
    ProjectMemberRole,
    RoleId,
    SessionMode,
    SessionStatus,
    StageId,
    is_valid_stage,
)

# Tipos de uso frecuente con constraints comunes.
NonEmptyStr = Annotated[str, Field(min_length=1, max_length=500)]
Slug = Annotated[str, Field(pattern=r"^[A-Z0-9]+(-[A-Za-z0-9]+)*-\d{4}-\d{2}-\d{2}$")]
"""Slug en el formato `[TIPO]-[topic]-[YYYY-MM-DD]` — espejo del filename builder."""


class _Base(BaseModel):
    """Config común — `model_config` compartido entre entidades de salida.

    Serializamos en **camelCase** porque el frontend (TS) usa camelCase en sus
    tipos (`autorOid`, `hasMore`, `valueScore`, ...). Pydantic acepta también
    snake_case al construir instancias en código Python (`populate_by_name`).
    Así el dominio mantiene PEP 8 y el contrato HTTP queda directo al
    frontend sin mappers manuales.
    """

    model_config = ConfigDict(
        # Aceptar enum values además de instancias del enum al deserializar.
        use_enum_values=True,
        # Inmutables por defecto — operaciones devuelven una nueva instancia.
        frozen=False,
        # Validar también en asignaciones (no solo en construcción).
        validate_assignment=True,
        # Mapeo snake_case (Python) ↔ camelCase (JSON al frontend). FastAPI
        # serializa response models con `by_alias=True` por default, así que
        # las respuestas salen en camelCase. `populate_by_name=True` deja que
        # el dominio siga construyendo instancias en snake_case desde Python.
        alias_generator=to_camel,
        populate_by_name=True,
        # Documenta los ejemplos en /docs.
        json_schema_extra={"$comment": "SQA KB domain entity"},
    )


# ===========================================================================
# Identidad y autorización
# ===========================================================================


class User(_Base):
    """Usuario autenticado del sistema (Fase 9 — multi-tenant).

    Espejo del `AuthUser` en frontend. En backend Fase 1B se crea/actualiza
    desde el JWT de Entra ID en el primer login.

    El modelo de permisos tiene **dos ejes ortogonales**:
    - `role_id` (este campo): rol global — `colaborador` o `gk_lead`.
    - `project_members.role` (otra tabla): rol per-proyecto —
      `project_owner` o `member`. Ver `ProjectMembership`.

    Los campos `carpetas_owned` y `puede_*` son **legacy** de Fase 1 y se
    ignoran a partir de Fase 9 (la capacidad efectiva se calcula con
    `PermissionPolicy` + rol global + membership del proyecto activo). Se
    mantienen en el modelo para no romper la wire del frontend Fase 5-8
    mientras el selector global no esté wireado (Fase 9.8). Limpieza
    definitiva: Fase 11.
    """

    oid: NonEmptyStr = Field(description="Entra Object ID (claim `oid` del JWT)")
    email: NonEmptyStr
    name: NonEmptyStr
    role_id: RoleId
    carpetas_owned: list[CategoryCode] = Field(
        default_factory=list,
        description="LEGACY (Fase 1): carpetas del rol owner. Vacío en Fase 9.",
    )
    puede_gobernar_taxonomia: bool = False
    """LEGACY (Fase 1). Reemplazado por `is_gk_lead` + per-proyecto."""
    puede_aprobar_taxonomia: bool = False
    """LEGACY (Fase 1). Reemplazado por per-proyecto `project_owner`."""
    puede_ver_metricas_globales: bool = False
    """LEGACY (Fase 1). En Fase 9 solo `gk_lead` ve métricas globales."""
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_admin(self) -> bool:
        """Admin global = solo GK Lead (Fase 9).

        El antiguo `owner` global desapareció — su semántica pasó a
        `project_owner` per-proyecto, que NO es admin global. Los pantallas
        que dependían de `is_admin` para gating se actualizan en Fase 9.6+
        para usar `PermissionPolicy(user, project)`.

        Decorado con `computed_field` para que aparezca en `.model_dump()`
        y en la respuesta JSON del API — el frontend espera este campo.
        """
        return self.role_id == RoleId.GKLEAD


# ===========================================================================
# Proyectos (Fase 9 — multi-tenant)
# ===========================================================================


class Project(_Base):
    """Espacio de trabajo aislado con su propia base de conocimiento.

    Cada documento, sesión, query e ítem de ingesta pertenece a UN proyecto
    (via `project_id` FK). Las consultas RAG están scopeadas obligatoriamente.
    Ver ADR 0009.
    """

    id: NonEmptyStr
    """UUID4. El proyecto seed se llama `gk-general` (slug)."""
    slug: Annotated[str, Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")]
    """Identificador legible URL-safe (kebab-case, sin acentos)."""
    name: NonEmptyStr
    description: str = ""
    owner_oid: NonEmptyStr
    """OID del usuario designado por GK Lead como `project_owner` inicial."""
    created_at: datetime
    archived_at: datetime | None = None
    """ISO timestamp. Si está, el proyecto está archivado (read-only)."""


class ProjectMember(_Base):
    """Membresía de un usuario en un proyecto (Fase 9).

    Tabla compuesta `(project_id, user_oid)` PK. El `role` define qué puede
    hacer dentro del proyecto — independiente del rol global del usuario.
    """

    project_id: NonEmptyStr
    user_oid: NonEmptyStr
    role: ProjectMemberRole
    added_at: datetime


class ProjectMembership(_Base):
    """Vista derivada para autorizar al usuario en un proyecto (Fase 9).

    Combina el rol global del `User` con su rol per-proyecto (si existe). Es
    un value object — no se persiste, se construye on-demand por la
    `PermissionPolicy` en cada request. Centraliza las decisiones de
    autorización para que no se filtren a la capa HTTP.
    """

    project_id: NonEmptyStr
    user_oid: NonEmptyStr
    global_role: RoleId
    project_role: ProjectMemberRole | None = None
    """`None` si el usuario no es miembro. GK Lead opera sin necesidad de
    membership, pero las acciones quedan auditadas como override."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_gk_lead(self) -> bool:
        return self.global_role == RoleId.GKLEAD

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_project_owner(self) -> bool:
        return self.project_role == ProjectMemberRole.PROJECT_OWNER

    @computed_field  # type: ignore[prop-decorator]
    @property
    def can_read(self) -> bool:
        """Lee documentos, hace queries, ve la cola de ingesta."""
        return self.is_gk_lead or self.project_role is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def can_ingest(self) -> bool:
        """Sube documentos al pipeline (quedan pendientes de aprobación)."""
        return self.is_gk_lead or self.project_role is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def can_approve(self) -> bool:
        """Aprueba/rechaza ítems de ingesta. Principal en `project_owner`;
        habilitado en `gk_lead` como override de auditoría."""
        return self.is_gk_lead or self.is_project_owner

    @computed_field  # type: ignore[prop-decorator]
    @property
    def can_manage_members(self) -> bool:
        """Añade/quita miembros del proyecto."""
        return self.is_gk_lead or self.is_project_owner

    @computed_field  # type: ignore[prop-decorator]
    @property
    def can_edit_taxonomy(self) -> bool:
        """Modifica taxonomía del proyecto (no la global)."""
        return self.is_gk_lead or self.is_project_owner

    @computed_field  # type: ignore[prop-decorator]
    @property
    def can_run_documentation_session(self) -> bool:
        """Corre la sesión guiada con el agente."""
        return self.is_gk_lead or self.is_project_owner


# ===========================================================================
# Sesiones y mensajes (chat con Aria)
# ===========================================================================


class CitationPayload(_Base):
    """Citación a un documento del KB. Emitida como evento SSE `citation`."""

    document_id: NonEmptyStr
    filename: NonEmptyStr
    section: NonEmptyStr
    snippet: NonEmptyStr


class ClassificationPayload(_Base):
    """Sugerencia de clasificación que hace el agente."""

    category: CategoryCode
    document_type: DocTypeCode
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str | None = None


class ScoringPayload(_Base):
    """Scoring de captura. 4 dimensiones + valueScore agregado."""

    specificity: float = Field(ge=1.0, le=5.0)
    depth: float = Field(ge=1.0, le=5.0)
    reusability: float = Field(ge=1.0, le=5.0)
    uniqueness: float = Field(ge=1.0, le=5.0)
    value_score: float = Field(ge=1.0, le=5.0)


class TokenUsagePayload(_Base):
    """Costos por mensaje. Persistir aunque el frontend solo lo muestre a admins."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    model: NonEmptyStr


class DocumentArtifactPayload(_Base):
    """Documento generado por el agente en una sesión de captura."""

    document_id: NonEmptyStr
    filename: NonEmptyStr
    download_url: NonEmptyStr
    blob_path: NonEmptyStr


class Message(_Base):
    """Mensaje del usuario o del agente en una sesión.

    Mantiene la forma del frontend `AgentMessage` para que el contrato HTTP
    sea directo. Los timestamps y `duration_ms` los completa el backend.
    """

    id: NonEmptyStr
    session_id: NonEmptyStr
    role: MessageRole
    content: str
    stage: StageId | None = None
    status: MessageStatus
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    classification: ClassificationPayload | None = None
    citations: list[CitationPayload] = Field(default_factory=list)
    scoring: ScoringPayload | None = None
    artifacts: list[DocumentArtifactPayload] = Field(default_factory=list)
    token_usage: TokenUsagePayload | None = None
    error_payload: str | None = Field(default=None, alias="error")

    @model_validator(mode="after")
    def _validate_stage(self) -> Self:
        if self.stage is not None and not is_valid_stage(self.stage):
            from sqa_kb.domain.errors import ValidationError

            raise ValidationError(f"Stage inválido: {self.stage!r}")
        return self


class Session(_Base):
    """Sesión de conversación con Aria (modo A, B o C).

    Espejo de `AgentSession` del frontend. Pausa/reanuda están modeladas
    a través de `status` (active ↔ paused).
    """

    id: NonEmptyStr
    owner_oid: NonEmptyStr
    """Entra OID del dueño. Filtro obligatorio en todos los queries
    de sesión por [[project-security-idor-check]]."""
    mode: SessionMode
    title: NonEmptyStr
    status: SessionStatus
    current_stage: StageId | None = None
    message_count: int = Field(ge=0, default=0)
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Taxonomía
# ===========================================================================


class Category(_Base):
    """Carpeta temática del KB."""

    code: CategoryCode
    label: NonEmptyStr
    docs: int = Field(ge=0, default=0)
    vigentes: int = Field(ge=0, default=0)
    autoritativos: int = Field(ge=0, default=0)
    score_avg: float = Field(ge=0.0, le=5.0, default=0.0)
    obsolescencia: int = Field(
        ge=0,
        default=0,
        description="Cantidad de docs por revisar/refrescar.",
    )


class DocType(_Base):
    """Tipo de documento del playbook SQA."""

    code: DocTypeCode
    label: NonEmptyStr


# ===========================================================================
# Taxonomía por proyecto (Fase 9.4)
# ===========================================================================


class ProjectCategory(_Base):
    """Override / extensión per-proyecto del catálogo global de carpetas.

    Dos modos:
    - `is_override=True`: el `code` coincide con uno global y se reemplaza
      el `label` para este proyecto.
    - `is_override=False`: el `code` es nuevo (no existe en el global) —
      extensión exclusiva del proyecto.

    En ambos casos, `parent_global_code` puede apuntar a un global como
    referencia (útil cuando una extensión "deriva" de una categoría global).
    """

    project_id: NonEmptyStr
    code: NonEmptyStr
    """Código de carpeta — puede ser un código global (override) o uno
    nuevo (extensión)."""
    label: NonEmptyStr
    parent_global_code: str | None = None
    is_override: bool = False


class ProjectDocType(_Base):
    """Override / extensión per-proyecto del catálogo global de tipos."""

    project_id: NonEmptyStr
    code: NonEmptyStr
    label: NonEmptyStr
    parent_global_code: str | None = None
    is_override: bool = False


class EffectiveCategoryEntry(_Base):
    """Entrada del catálogo efectivo de carpetas (Fase 9.4).

    Diferencia con `Category`: `code` es `str` plano (no `CategoryCode`)
    para admitir extensiones per-proyecto con códigos fuera del enum
    global. Los counters quedan en 0 para entradas extension — el
    refresh global no las cuenta."""

    code: NonEmptyStr
    label: NonEmptyStr
    docs: int = Field(ge=0, default=0)
    vigentes: int = Field(ge=0, default=0)
    autoritativos: int = Field(ge=0, default=0)
    score_avg: float = Field(ge=0.0, le=5.0, default=0.0)
    obsolescencia: int = Field(ge=0, default=0)
    is_project_extension: bool = False
    """True si la entrada no existe en el catálogo global (es exclusiva
    del proyecto)."""


class EffectiveDocTypeEntry(_Base):
    """Entrada del catálogo efectivo de tipos."""

    code: NonEmptyStr
    label: NonEmptyStr
    is_project_extension: bool = False


class EffectiveTaxonomy(_Base):
    """Vista derivada (sin persistir) del catálogo efectivo de un proyecto.

    Resulta de mergear el catálogo global con los overrides + extensiones
    del proyecto. La construye `ProjectTaxonomyService.effective(...)`.

    El frontend lo consume para poblar selectores (carpeta / tipo) en el
    formulario de aprobación de ingesta y en el classifier del agente.
    """

    project_id: NonEmptyStr
    categories: list[EffectiveCategoryEntry]
    doc_types: list[EffectiveDocTypeEntry]


# ===========================================================================
# Documentos del KB
# ===========================================================================


class CaptureScore(_Base):
    """Scoring persistido en BD (espejo del payload de streaming)."""

    document_id: NonEmptyStr
    specificity: float = Field(ge=1.0, le=5.0)
    depth: float = Field(ge=1.0, le=5.0)
    reusability: float = Field(ge=1.0, le=5.0)
    uniqueness: float = Field(ge=1.0, le=5.0)
    value_score: float = Field(ge=1.0, le=5.0)
    computed_at: datetime


class IncomingCitation(_Base):
    """Citación recibida por un documento desde otra pieza del KB."""

    source_doc_id: NonEmptyStr
    source_title: NonEmptyStr
    source_folder: CategoryCode
    section: NonEmptyStr
    snippet: NonEmptyStr
    cited_at: datetime


class Document(_Base):
    """Documento indexado del KB (texto + metadata, sin el binario)."""

    id: Slug
    """Slug `[TIPO]-[topic]-[YYYY-MM-DD]` — mismo que produce el agente."""
    project_id: NonEmptyStr | None = None
    """UUID del proyecto al que pertenece. **None** solo durante migración
    legacy / tests que no pasaron por el pipeline post-Fase 9 — el mapper
    cae a `gk-general` cuando es None. Nuevas inserciones desde
    `IngestionService.approve` ya lo cablean explícitamente."""
    titulo: NonEmptyStr
    carpeta: CategoryCode
    tipo: DocTypeCode
    autoritativo: bool
    estado: DocStatus
    autor_oid: NonEmptyStr | None = None
    """Entra OID del autor. None solo para legacy migrados sin oid conocido."""
    autor_name: NonEmptyStr = Field(alias="autor")
    """Nombre del autor. El frontend lo lee como `autor` (display name)."""
    autor_role: NonEmptyStr = Field(alias="rol")
    """Rol del autor al momento de capturar. Frontend lo lee como `rol`."""
    fecha: datetime
    revision: datetime
    version: NonEmptyStr
    citas: int = Field(ge=0, default=0)
    """Cantidad de citas recibidas (denormalizado para listado rápido)."""
    score: float = Field(ge=0.0, le=5.0, default=0.0)
    """`value_score` denormalizado para listado rápido."""
    anonimizado: bool = False
    fragmentos: int = Field(ge=0, default=0)
    """Chunks vectoriales del doc (Fase 3 RAG)."""
    paginas: int = Field(ge=0, default=0)
    formato: NonEmptyStr
    aprobador_name: NonEmptyStr | None = Field(default=None, alias="aprobador")
    """Nombre del aprobador. Frontend lo lee como `aprobador`."""
    fecha_aprobacion: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    blob_path: NonEmptyStr | None = None
    """Path en Azure Blob Storage. None para docs todavía no persistidos."""


class DocumentDetail(Document):
    """Document + datos cargados on-demand para la vista de detalle."""

    incoming_citations: list[IncomingCitation] = Field(default_factory=list)
    resumen: str = ""


class DocumentChunk(_Base):
    """Pieza vectorial de un documento indexado (Fase 3 RAG).

    `embedding` es opcional porque puede haber chunks recién creados sin
    vector (raro en el flujo normal — el indexer embedea antes del insert,
    pero hay un período de unos ms entre INSERT y commit donde el campo
    podría estar NULL en lecturas concurrentes). El dominio lo modela
    como opcional para no mentir.

    `metadata` guarda: `strategy`, `section_title`, `token_count`, `path`
    (hierarchical), `slide_number` (per_slide), `oversized_split` (bool).
    Queries del retriever no filtran por esos campos — solo se exponen
    al frontend en el response.
    """

    id: NonEmptyStr
    document_id: NonEmptyStr
    chunk_index: int = Field(ge=0)
    content: NonEmptyStr
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ===========================================================================
# Ingesta (modo C — documento aprobado que se sube al KB)
# ===========================================================================


class IngestionItem(_Base):
    """Documento aprobado en cola de procesamiento (extracción + indexación)."""

    id: NonEmptyStr
    project_id: NonEmptyStr
    """UUID del proyecto al que pertenece el item. Scoping multi-tenant
    desde Fase 9.3 — el documento generado al aprobar hereda este `project_id`."""
    filename: NonEmptyStr
    size_bytes: int = Field(ge=0)
    paginas: int = Field(ge=0, default=0)
    carpeta_sugerida: CategoryCode | None = None
    tipo_sugerido: DocTypeCode | None = None
    aprobador_oid: NonEmptyStr | None = None
    aprobador_name: str = ""
    fecha_aprobacion: datetime | None = None
    fuente_original: str = ""
    """URL, share de SharePoint, ruta, link de Drive, etc."""
    version: str = ""
    status: IngestionStatus
    uploaded_by_oid: NonEmptyStr
    uploaded_at: datetime
    blob_path: NonEmptyStr | None = None
    error_detail: str | None = None
    """Si `status=rechazado` o falla extracción, el motivo."""


# ===========================================================================
# Consultas (modo B — pregunta al KB sin captura)
# ===========================================================================


class Query(_Base):
    """Consulta del modo B. Persistida para análisis y gap detection."""

    id: NonEmptyStr
    project_id: NonEmptyStr
    """UUID del proyecto al que pertenece la consulta. Scoping multi-tenant
    desde Fase 9.3 — no hay queries cross-project."""
    user_oid: NonEmptyStr
    session_id: NonEmptyStr | None = None
    text: NonEmptyStr
    asked_at: datetime
    answered_at: datetime | None = None
    has_result: bool = False
    """False ⇒ "sin resultado" — alimenta KPI del dashboard."""


class QueryCitation(_Base):
    """Citación que una consulta hizo a un documento (para grafo de citas)."""

    query_id: NonEmptyStr
    document_id: NonEmptyStr
    section: NonEmptyStr
    snippet: NonEmptyStr


# ===========================================================================
# Skills (prompts del agente, editables desde admin)
# ===========================================================================


class Skill(_Base):
    """Skill del agente — prompt o regla editable sin desplegar.

    Se cargan al system prompt del agente vía `Skills loader` (Fase 2).
    En Fase 9 (admin frontend) se exponen para edición con editor Markdown.
    """

    id: NonEmptyStr
    name: NonEmptyStr
    description: str = ""
    body_markdown: str = ""
    enabled: bool = True
    version: int = Field(ge=1, default=1)
    updated_by_oid: NonEmptyStr | None = None
    updated_at: datetime


# ===========================================================================
# Audit log (governance)
# ===========================================================================


class AuditLog(_Base):
    """Evento de auditoría inmutable.

    Por [[project-security-idor-check]]: cuando un admin (Owner/GK Lead)
    accede a una sesión que no es suya, queda registrado aquí — incluido
    el caso donde el admin sí es dueño, para trazabilidad pareja.

    Si TI decide audit log central compartido entre apps, ver el dual-write
    descripto en docs/alineacion-arquitectura-ti.md §2.5.
    """

    id: NonEmptyStr
    actor_oid: NonEmptyStr
    event_type: NonEmptyStr
    """Ej: `session.created`, `document.marked_authoritative`, `taxonomy.changed`."""
    resource_id: NonEmptyStr | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    at: datetime


# ===========================================================================
# Dashboard / actividad (frontend Fase 7)
# ===========================================================================


class HotTopic(_Base):
    """Tema en demanda con detección de gap (alta consulta + pocas citas)."""

    topic: NonEmptyStr
    queries_30d: int = Field(ge=0)
    citation_count: int = Field(ge=0)
    is_gap: bool = False


class ActorRef(_Base):
    """Referencia compacta a un usuario — usada en feed de actividad.

    El frontend espera `actor: { oid, name }` (no `actor_oid` + `actor_name`
    sueltos), así que modelamos el dominio igual y dejamos al mapper armar
    el `ActorRef` desde las columnas `actor_oid` + `actor_name` de la tabla.
    """

    oid: NonEmptyStr
    name: NonEmptyStr


class RecentActivityItem(_Base):
    """Item del feed de actividad reciente."""

    id: NonEmptyStr
    type: ActivityType
    actor: ActorRef
    at: datetime
    summary: NonEmptyStr
    ref_url: str | None = None


class MyCapturesStats(_Base):
    """Stats personales del Capturador (vista /my-captures)."""

    total_captures: int = Field(ge=0, default=0)
    total_citations_received: int = Field(ge=0, default=0)
    avg_score: float = Field(ge=0.0, le=5.0, default=0.0)
    last_captured_at: datetime | None = None
