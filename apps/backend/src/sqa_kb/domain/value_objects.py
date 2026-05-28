"""Value objects del dominio — enums y tipos inmutables sin identidad propia.

Espejo de los códigos definidos en `ROADMAP-IMPLEMENTACION-SQA-KB.md` §7
(taxonomía SQA) y §10 (etapas del agente Aria). Estos códigos son contrato
con el frontend (`apps/frontend/src/types/domain.ts`) — no cambiar nombres
ni valores sin actualizar ambos lados.
"""

from __future__ import annotations

from enum import StrEnum


class CategoryCode(StrEnum):
    """Carpetas temáticas del KB. Son 8, cerradas."""

    PROC = "PROC"  # Procesos
    TEC = "TEC"  # Técnico
    ARQ = "ARQ"  # Arquitectura
    HERR = "HERR"  # Herramientas
    NEG = "NEG"  # Negocio
    ENV = "ENV"  # Ambientes
    EST = "EST"  # Estándares
    CONT = "CONT"  # Contexto


class DocTypeCode(StrEnum):
    """Tipos de documento del playbook SQA. Son 11, cerradas."""

    POL = "POL"  # Política
    PROC = "PROC"  # Procedimiento
    GUIA = "GUIA"  # Guía
    INST = "INST"  # Instructivo
    SERV = "SERV"  # Servicio
    MTEC = "MTEC"  # Memoria técnica
    ACEL = "ACEL"  # Acelerador
    UEN = "UEN"  # UEN (Unidad Estratégica de Negocio)
    ARCL = "ARCL"  # Arquetipo cliente
    FORM = "FORM"  # Formato
    PRES = "PRES"  # Presentación


class DocStatus(StrEnum):
    """Ciclo de vida de un documento del KB."""

    BORRADOR = "borrador"
    GENERADO = "generado"
    EN_REVISION = "en-revision"
    APROBADO = "aprobado"
    VIGENTE = "vigente"
    OBSOLETO = "obsoleto"
    REEMPLAZADO = "reemplazado"
    ARCHIVADO = "archivado"


class SessionMode(StrEnum):
    """Modo de la conversación con Aria. A=captura, B=consulta, C=ingesta."""

    CAPTURA = "captura"
    CONSULTA = "consulta"
    INGESTA = "ingesta"


class SessionStatus(StrEnum):
    """Estado del ciclo de vida de una sesión."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MessageRole(StrEnum):
    """Quién emite un mensaje en la conversación."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    """Estado de un mensaje del agente — refleja el ciclo del streaming SSE."""

    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETE = "complete"
    ERROR = "error"


class IngestionStatus(StrEnum):
    """Estado de un item de la cola de ingesta (modo C)."""

    PENDIENTE_METADATA = "pendiente-metadata"
    LISTO = "listo"
    EN_REVISION = "en-revision"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    INDEXADO = "indexado"


class RoleId(StrEnum):
    """Roles globales del sistema (Fase 9 — multi-tenant).

    Refactor desde 3 roles (`capturador`, `owner`, `gklead`) a 2 ejes:
    - **Global** (este enum): qué puede hacer en la plataforma.
    - **Per-proyecto** (`ProjectMemberRole`): qué puede hacer dentro de un
      proyecto específico.

    El rol `owner` global desaparece — su semántica de aprobador pasa a
    `project_owner` per-proyecto. El antiguo `capturador` se renombra a
    `colaborador` (es más fiel al uso real: captura + consulta + revisa).

    Ver `docs/architecture/adr/0009-multi-tenant-projects.md` §D2.
    """

    COLABORADOR = "colaborador"
    """Default. Opera dentro de proyectos donde es miembro."""
    GKLEAD = "gklead"
    """Super-admin. Crea proyectos, audita, supervisa todos los proyectos."""


class ProjectMemberRole(StrEnum):
    """Rol per-proyecto en `project_members.role` (Fase 9).

    Independiente del rol global: un usuario `colaborador` global puede ser
    `project_owner` en un proyecto y `member` en otro. El `gk_lead` global
    no necesita membership (acceso por privilegio).
    """

    PROJECT_OWNER = "project_owner"
    """Admin del proyecto: miembros, taxonomía, sesión de doc, aprobaciones."""
    MEMBER = "member"
    """Consume y aporta: queries, ingesta (queda pendiente de aprobar)."""


# StageId del agente — numéricas 0-5 para modo A, strings para B y C.
# Mantengo como union literal para validación estricta con Pydantic.
StageId = int | str
"""
Etapas del agente Aria:
- 0..5: numéricas, ETAPAS del modo captura (bienvenida → identificación → captura libre →
  profundización → validación → generación)
- "C": stage único del modo consulta
- "I": stage único del modo ingesta

Validar con `is_valid_stage()` antes de aceptar.
"""

VALID_STAGE_INTS: frozenset[int] = frozenset({0, 1, 2, 3, 4, 5})
VALID_STAGE_STRS: frozenset[str] = frozenset({"C", "I"})


def is_valid_stage(value: object) -> bool:
    """`True` si `value` es un StageId válido (0..5, 'C' o 'I')."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value in VALID_STAGE_INTS
    if isinstance(value, str):
        return value in VALID_STAGE_STRS
    return False


class ActivityType(StrEnum):
    """Tipos de evento del feed de actividad (dashboard)."""

    CAPTURA = "captura"
    INGESTA = "ingesta"
    CONSULTA = "consulta"
    TAXONOMIA = "taxonomia"
