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
    """Roles operativos definidos en [[project-roles-capacidades]]."""

    CAPTURADOR = "capturador"  # Colaborador (QA, automation, áreas transversales)
    OWNER = "owner"  # Responsable de una carpeta temática
    GKLEAD = "gklead"  # GK Lead (Líder de Gestión del Conocimiento)


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
