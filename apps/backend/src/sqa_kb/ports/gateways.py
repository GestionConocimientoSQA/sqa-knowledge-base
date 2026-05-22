"""Interfaces de servicios externos.

Estos puertos abstraen integraciones HTTP/SDK:
- `LlmGateway` — Claude vía Anthropic directo o LiteLLM proxy.
- `BlobStorage` — Azure Blob (o Azurite en local).
- `EmailSender` — Azure Communication Services (Fase 2 con notificaciones).
- `PiiFilter` — Presidio (si TI lo activa).
- `TokenValidator` — Entra ID JWT (o dev provider en local).

Mantener la firma agnóstica del SDK subyacente. Si Anthropic SDK cambia
de versión o cambiamos a OpenAI Azure, el adapter cambia, no el dominio.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sqa_kb.domain.entities import User


# ===========================================================================
# Auth / token validation
# ===========================================================================


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Claims relevantes extraídos del JWT. Agnostic del provider."""

    oid: str
    email: str
    name: str
    groups: tuple[str, ...] = ()
    """Groups claim de Entra (opcional). En dev provider queda vacío."""


@runtime_checkable
class TokenValidator(Protocol):
    """Valida un Bearer token y devuelve los claims o lanza UnauthorizedError.

    Implementaciones concretas:
    - `adapters/auth/entra.py` — valida firma JWT contra JWKS de Entra ID.
    - `adapters/auth/dev.py` — acepta tokens fake del frontend stub MSAL
      (solo si `SQA_KB_APP_ENV ∈ {dev, test}`).
    """

    async def validate(self, bearer_token: str) -> TokenClaims: ...

    async def resolve_user(self, claims: TokenClaims) -> User: ...
    """Combina claims + tabla local de usuarios para devolver el `User`
    completo con permisos finos (no solo `is_admin`)."""


# ===========================================================================
# LLM gateway
# ===========================================================================


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Mensaje en el formato del LLM (role + content). No es lo mismo que
    `domain.entities.Message` — este es el wire format del provider."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    """Resultado de una llamada non-streaming al LLM."""

    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str


@dataclass(frozen=True, slots=True)
class LlmStreamEvent:
    """Evento de streaming. `kind` distingue el tipo de chunk recibido."""

    kind: str  # "text" | "tool_use" | "stop" | "error"
    payload: Mapping[str, object]


@runtime_checkable
class LlmGateway(Protocol):
    """Cliente abstracto de modelos LLM. Implementaciones:

    - `adapters/llm/anthropic_direct.py` — anthropic SDK con tu API key.
    - `adapters/llm/litellm.py` — HTTP al proxy gestionado por TI.

    El cliente acepta opcionalmente `metadata` para trazas (request_id,
    user_oid, session_id) — el adapter las inyecta como headers/params
    del provider para que aparezcan en Langfuse / LiteLLM Dashboard.
    """

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> LlmCompletion: ...

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> AsyncIterator[LlmStreamEvent]: ...


# ===========================================================================
# Blob storage
# ===========================================================================


@dataclass(frozen=True, slots=True)
class BlobMetadata:
    """Metadata mínima de un blob."""

    path: str
    size_bytes: int
    content_type: str
    etag: str


@runtime_checkable
class BlobStorage(Protocol):
    """Storage de archivos (uploads, documentos generados, etc.).

    Adapters:
    - `adapters/blob/azure.py` — azure-storage-blob (Managed Identity en
      Azure, connection string en local con Azurite).
    """

    async def upload(
        self,
        *,
        container: str,
        path: str,
        data: bytes,
        content_type: str,
    ) -> BlobMetadata: ...

    async def download(self, *, container: str, path: str) -> bytes: ...

    async def delete(self, *, container: str, path: str) -> None: ...

    async def signed_url(
        self,
        *,
        container: str,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str: ...


# ===========================================================================
# PII filter (opcional — solo si Presidio está activo)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class PiiFilterResult:
    """Texto procesado por Presidio."""

    text: str
    replacements: int
    """Cuántos elementos PII se anonimizaron."""


@runtime_checkable
class PiiFilter(Protocol):
    """Anonimización pre-LLM. Si `presidio_enabled=False`, el adapter
    no-op devuelve el input intacto y `replacements=0`."""

    async def anonymize(self, text: str) -> PiiFilterResult: ...


# ===========================================================================
# Email (Fase 2 — notificaciones a Owners)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: tuple[str, ...]
    subject: str
    body_html: str
    body_text: str = ""


@runtime_checkable
class EmailSender(Protocol):
    """Adapter: Azure Communication Services (azure-communication-email)."""

    async def send(self, message: EmailMessage) -> None: ...


# ===========================================================================
# Health checks (1A.5)
# ===========================================================================


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """Resultado de un verificador de salud."""

    name: str
    healthy: bool
    detail: str = ""
    duration_ms: float = 0.0


@runtime_checkable
class HealthCheck(Protocol):
    """Verificador individual: DB, blob, LLM gateway, etc.

    El aggregator (`api/health.py`) corre todos los registrados en paralelo
    y combina el resultado. Cada implementación maneja su propio timeout
    y devuelve `healthy=False` antes que dejar colgado el health check.
    """

    @property
    def name(self) -> str: ...

    async def check(self) -> HealthCheckResult: ...
