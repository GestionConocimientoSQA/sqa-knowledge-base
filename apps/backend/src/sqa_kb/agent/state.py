"""Estado del agente conversacional — espejo del §16.2 del ROADMAP.

LangGraph soporta TypedDict, dataclass o Pydantic BaseModel como state.
Elegimos **Pydantic v2** porque:
- Ya lo usamos en el dominio (consistencia).
- Validamos al construir (atajos como enum + score 1.0-5.0 fallan rápido).
- Funciona con `JsonPlusSerializer` del checkpointer oficial.

**Decisión Fase 2.1**: estado *plano* (no anidado) por simplicidad de
serialización + checkpoint. Si crece, se factoriza por modo.

Convenciones:
- Tipos opcionales con `default=None` (no `default_factory`) si vienen del
  LLM y pueden faltar.
- Listas siempre con `default_factory=list` (nunca compartidas).
- Enums como Literal[str] — el grafo decide en runtime, evitamos `Enum`
  para no acoplar con `domain.value_objects`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Aliases para legibilidad — matchean los del ROADMAP §16.2.
SessionMode = Literal["capture", "consultation", "ingestion"]
"""Tres modos del agente: captura (A), consulta (B), ingesta (C)."""

UpdateDecision = Literal["update", "complement", "review_first"]
"""Decisión del usuario cuando se detecta un doc existente similar."""

RelevanceLevel = Literal["alta", "media", "sin_resultados"]
"""Auto-clasificación del agente sobre la calidad del resultado de búsqueda."""


# ===========================================================================
# Sub-modelos
# ===========================================================================


class Classification(BaseModel):
    """Sugerencia de carpeta + tipo de documento. El agente la propone, el
    usuario confirma en ETAPA 1."""

    model_config = ConfigDict(extra="forbid")

    category: str
    """8 carpetas: PROC, TEC, HERR, NEG, ENV, EST, ARQ, CONT."""
    document_type: str
    """11 tipos: POL, PROC, GUIA, INST, SERV, MTEC, ACEL, UEN, ARCL, FORM, PRES."""
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ExistingDocument(BaseModel):
    """Documento parecido encontrado en el KB durante ETAPA 1."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    category: str
    document_type: str
    distance: float = Field(ge=0.0)
    """Distancia vectorial. <= 0.55 dispara workflow de update/complement."""
    created_at: str


class RetrievedChunk(BaseModel):
    """Chunk del RAG (Fase 3). Persistido acá para que el agente lo cite."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    content: str
    section_title: str | None = None
    score: float
    is_authoritative: bool


class Citation(BaseModel):
    """Cita emitida hacia el usuario. Espejo del SSE event `citation`."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    chunk_id: str
    section: str | None = None
    snippet: str
    position: int = Field(ge=0)


class Traceability(BaseModel):
    """Metadata de origen — obligatoria en modo ingesta (§16 ROADMAP)."""

    model_config = ConfigDict(extra="forbid")

    approved_by: str
    approval_date: str
    source_origin: str
    source_version: str | None = None


class CaptureScoring(BaseModel):
    """Scoring de 4 dimensiones + valor agregado. ETAPA 5."""

    model_config = ConfigDict(extra="forbid")

    specificity: int = Field(ge=1, le=5)
    depth: int = Field(ge=1, le=5)
    reusability: int = Field(ge=1, le=5)
    uniqueness: int = Field(ge=1, le=5)
    value_score: float = Field(ge=1.0, le=5.0)
    observations: str


class AttachmentRef(BaseModel):
    """Adjunto referenciado por el estado (no el blob real)."""

    model_config = ConfigDict(extra="forbid")

    attachment_id: str
    filename: str
    mime_type: str
    """`application/pdf`, `image/png`, etc."""
    blob_path: str | None = None


# ===========================================================================
# AgentState — el estado completo que LangGraph checkpointea
# ===========================================================================


class AgentState(BaseModel):
    """Estado del agente persistido por turno. **Plano** a propósito —
    los sub-modelos están denormalizados.

    Convención sobre defaults:
    - Campos que el agente llena en ETAPA 1+ son `None` al inicio.
    - Listas que crecen turno a turno arrancan vacías.
    - Counters numéricos en 0.

    LangGraph requiere que cada update del state sea un `dict` parcial:
    los nodos devuelven `{"messages": [...]}` y LangGraph fusiona. Pydantic
    valida el resultado en cada commit. Por eso `extra="forbid"` — si un
    nodo intenta meter una key fuera del schema, falla fast en lugar de
    perderse silenciosamente.
    """

    # LangGraph hace muchos partial updates por turno — no queremos quemar
    # CPU revalidando todo el state en cada asignación.
    model_config = ConfigDict(extra="forbid", validate_assignment=False)

    # === Identidad ===
    session_id: str
    user_id: str
    """OID de Entra ID del usuario dueño."""
    user_name: str
    user_role: str | None = None

    # === Modo y etapa ===
    mode: SessionMode
    current_stage: str
    """ETAPA actual. Strings libres porque hay numéricas (`ETAPA_0`-`5`)
    y de modos B/C (`consult_search`, `ingestion_extract`, etc.)."""
    previous_stage: str | None = None

    # === Mensajes ===
    messages: list[dict[str, Any]] = Field(default_factory=list)
    """Mensajes serializables a JSON. LangGraph también soporta BaseMessage
    de langchain-core, pero los guardamos como dict para no acoplar el
    state al SDK. Los nodos los reconvierten al pasar al LLM."""

    # === Skills ===
    active_skills: list[str] = Field(default_factory=list)
    """IDs de skills inyectados en el system prompt (Fase 2.2)."""

    # === CAPTURA (Modo A) ===
    topic: str | None = None
    classification: Classification | None = None
    classification_confirmed: bool = False
    existing_documents: list[ExistingDocument] = Field(default_factory=list)
    update_decision: UpdateDecision | None = None
    free_capture_blocks: list[str] = Field(default_factory=list)
    """Cada item es un bloque libre de captura (ETAPA 2)."""
    deep_dive_qa: dict[str, str] = Field(default_factory=dict)
    """Pregunta dirigida → respuesta del usuario (ETAPA 3)."""
    is_reusable_content: bool | None = None
    """Si True, ETAPA 5 dispara anonimización antes de generar."""
    summary_validated: bool = False
    generated_document_id: str | None = None
    capture_scoring: CaptureScoring | None = None

    # === CONSULTA (Modo B) ===
    current_query: str | None = None
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    relevance_level: RelevanceLevel | None = None

    # === INGESTA (Modo C) ===
    ingestion_item_id: str | None = None
    extracted_text: str | None = None
    sections_detected: int | None = None
    suggested_classification: Classification | None = None
    traceability: Traceability | None = None
    duplicate_check_result: list[ExistingDocument] = Field(default_factory=list)

    # === Adjuntos (transversal) ===
    attachments: list[AttachmentRef] = Field(default_factory=list)
    attachments_processed: bool = False

    # === Control de flujo ===
    needs_user_input: bool = False
    """True ⇒ el grafo pausa en interrupt esperando próximo mensaje."""
    awaiting_confirmation: str | None = None
    """Token semántico de qué se está confirmando ("classification",
    "summary", "update_decision", etc.). Lo lee el frontend para mostrar
    el chip apropiado."""
    last_error: str | None = None
    retry_count: int = Field(default=0, ge=0)

    # === Métricas acumuladas (cost tracker — Fase 2.2) ===
    total_input_tokens: int = Field(default=0, ge=0)
    total_output_tokens: int = Field(default=0, ge=0)
    total_cost_usd: float = Field(default=0.0, ge=0.0)


# Helper para construir el estado inicial de una sesión nueva. Mantiene
# defaults consistentes — los nodos no deberían construir AgentState
# directamente, solo retornar deltas parciales.
def initial_state(
    *,
    session_id: str,
    user_id: str,
    user_name: str,
    mode: SessionMode,
    user_role: str | None = None,
) -> AgentState:
    """Estado de arranque para `graph.ainvoke()`. Todos los campos de modo
    quedan en None — el grafo los llena turno a turno."""
    return AgentState(
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        mode=mode,
        current_stage="ETAPA_0",
    )
