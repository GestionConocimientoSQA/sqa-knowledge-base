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
    """Usuario autenticado del sistema.

    Espejo del `AuthUser` en frontend. En backend Fase 1B se crea/actualiza
    desde el JWT de Entra ID en el primer login.

    El modelo de permisos NO es un boolean `isAdmin` (ver
    [[project-roles-capacidades]]). Se modela con campos finos para que
    Owner sea admin sólo sobre `carpetas_owned`, GK Lead sea admin sobre
    todo, y Capturador sobre nada.
    """

    oid: NonEmptyStr = Field(description="Entra Object ID (claim `oid` del JWT)")
    email: NonEmptyStr
    name: NonEmptyStr
    role_id: RoleId
    carpetas_owned: list[CategoryCode] = Field(
        default_factory=list,
        description="Carpetas sobre las que Owner tiene admin. [] para Capturador y GK Lead.",
    )
    puede_gobernar_taxonomia: bool = False
    """Solo GK Lead. Permite crear/modificar carpetas, tipos, skills."""
    puede_aprobar_taxonomia: bool = False
    """Fase 2. Workflow de approval para cambios a la taxonomía."""
    puede_ver_metricas_globales: bool = False
    """GK Lead: True. Owner: True para sus carpetas (filtrado en query)."""
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_admin(self) -> bool:
        """Compatibilidad con el frontend: True si Owner o GK Lead.

        Decorado con `computed_field` para que aparezca en `.model_dump()`
        y en la respuesta JSON del API — el frontend espera este campo.

        En servicios del backend, **NO usar `is_admin`** — usar los flags
        finos. Este property existe solo para hidratar el `AuthUser` que
        el frontend espera hoy.
        """
        return self.role_id in (RoleId.OWNER, RoleId.GKLEAD)


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
