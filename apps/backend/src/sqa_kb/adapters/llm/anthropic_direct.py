"""Adapter `LlmGateway` → Anthropic SDK directo.

Implementa la interfaz `sqa_kb.ports.gateways.LlmGateway` usando el SDK
oficial `anthropic`. Es el default en dev local y en Fase 2 mientras TI
no provea un proxy LiteLLM gestionado.

Decisiones de diseño:
- **Async-first**: `AsyncAnthropic`, no se mezcla sync.
- **Prompt caching**: se acepta un `system` opcional con bloques marcables
  como `cache_control={"type": "ephemeral"}`. El caller (skills loader)
  define qué bloques cachear; el adapter solo los pasa al SDK.
- **Cost tracking**: cada `complete()` y el evento `stop` del `stream()`
  incluyen el cálculo en USD usando `pricing.estimate_cost_usd`.
- **Sin reintentos manuales**: el SDK ya hace exponential backoff con
  `max_retries=2` por default — alcanzan para el flujo del agente.
- **Metadata**: se inyecta como `metadata={"user_id": ...}` del SDK, que
  Anthropic loggea para auditoría. Útil para soporte cuando un usuario
  reporta un mensaje raro.

Mocking en tests: el método `__init__` acepta un cliente custom
(`AsyncAnthropic`-like) para inyectar un fake sin tocar HTTP.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message as AnthropicMessage

from sqa_kb.adapters.llm.pricing import estimate_cost_usd
from sqa_kb.ports.gateways import ChatMessage, LlmCompletion, LlmStreamEvent

logger = logging.getLogger(__name__)


# Anthropic SDK acepta diccionarios con `role` y `content`. Mantenemos la
# conversión acá para no leakear el formato del SDK al dominio.
_ROLE_SYSTEM = "system"
_ROLE_USER = "user"
_ROLE_ASSISTANT = "assistant"
_VALID_ROLES = frozenset({_ROLE_SYSTEM, _ROLE_USER, _ROLE_ASSISTANT})


class AnthropicDirectGateway:
    """`LlmGateway` concreto que habla directo con `api.anthropic.com`.

    No es Protocol implementer — duck-typing con `@runtime_checkable` ya
    cubre la verificación. Conservamos la clase concreta porque queremos
    inicializarla en `main.py` con la config inyectada.
    """

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str,
        client: AsyncAnthropic | None = None,
    ) -> None:
        """`client` opcional permite inyectar mocks en tests sin parchar
        el módulo. En runtime se construye uno fresco por gateway."""
        self._api_key = api_key
        self._default_model = default_model
        self._client = client or AsyncAnthropic(api_key=api_key, max_retries=2)

    # ===========================================================================
    # complete (non-streaming)
    # ===========================================================================

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> LlmCompletion:
        """Llama al modelo y devuelve la respuesta completa.

        Útil para nodos no-streaming del grafo (classify_topic, scoring,
        anonymize). El streaming va por `stream()`.
        """
        effective_model = model or self._default_model
        system_block, anthropic_messages = self._split_system(messages)

        kwargs: dict[str, Any] = {
            "model": effective_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }
        if system_block is not None:
            kwargs["system"] = system_block
        if metadata:
            kwargs["metadata"] = dict(metadata)

        result: AnthropicMessage = await self._client.messages.create(**kwargs)

        # `content` es una lista de bloques (text, tool_use, ...). Para
        # `complete()` esperamos solo text — concatenamos para devolver
        # un string plano.
        text = _extract_text(result)
        usage = _extract_usage(result)
        cost = estimate_cost_usd(
            model=effective_model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_write_tokens=usage["cache_write_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
        )
        return LlmCompletion(
            text=text,
            input_tokens=usage["input_tokens"] + usage["cache_read_tokens"]
            + usage["cache_write_tokens"],
            output_tokens=usage["output_tokens"],
            cost_usd=cost,
            model=effective_model,
        )

    # ===========================================================================
    # stream
    # ===========================================================================

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        metadata: Mapping[str, str] | None = None,
    ) -> AsyncIterator[LlmStreamEvent]:
        """Stream de tokens. Yielda `LlmStreamEvent` agnostic del SDK.

        Emite:
        - `kind="text"` por cada chunk de texto del modelo (`delta`)
        - `kind="tool_use"` cuando el modelo decide llamar una herramienta
        - `kind="stop"` al cerrar con `{input_tokens, output_tokens, cost_usd}`
        - `kind="error"` si la conexión falla a mitad de respuesta

        El caller decide qué hacer con los eventos — el endpoint SSE de
        2.6 los traduce a eventos `text-delta`, `tool-use`, `token-usage`.
        """
        effective_model = model or self._default_model
        system_block, anthropic_messages = self._split_system(messages)

        kwargs: dict[str, Any] = {
            "model": effective_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }
        if system_block is not None:
            kwargs["system"] = system_block
        if metadata:
            kwargs["metadata"] = dict(metadata)

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    converted = _convert_event(event)
                    if converted is not None:
                        yield converted

                # Acumulado final — incluye usage real del modelo.
                final = await stream.get_final_message()
                usage = _extract_usage(final)
                cost = estimate_cost_usd(
                    model=effective_model,
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    cache_write_tokens=usage["cache_write_tokens"],
                    cache_read_tokens=usage["cache_read_tokens"],
                )
                yield LlmStreamEvent(
                    kind="stop",
                    payload={
                        "input_tokens": usage["input_tokens"]
                        + usage["cache_read_tokens"]
                        + usage["cache_write_tokens"],
                        "output_tokens": usage["output_tokens"],
                        "cache_read_tokens": usage["cache_read_tokens"],
                        "cache_write_tokens": usage["cache_write_tokens"],
                        "cost_usd": cost,
                        "model": effective_model,
                        "stop_reason": final.stop_reason or "",
                    },
                )
        except Exception as exc:  # noqa: BLE001 — re-emit como evento, no romper grafo
            logger.exception("anthropic stream falló: %s", exc)
            yield LlmStreamEvent(
                kind="error",
                payload={"message": str(exc), "type": exc.__class__.__name__},
            )

    # ===========================================================================
    # Helpers internos
    # ===========================================================================

    @staticmethod
    def _split_system(
        messages: Sequence[ChatMessage],
    ) -> tuple[str | None, list[dict[str, str]]]:
        """Separa system prompt del resto. Anthropic espera el system como
        argumento top-level, no embebido en `messages`.

        Reglas:
        - `messages` no puede estar vacía (Anthropic exige al menos 1 user msg).
        - Múltiples system se concatenan con `\\n\\n` — en la práctica el
          caller pasa uno solo (system prompt + skills).
        - Tiene que haber al menos un mensaje no-system, sino la API rechaza.

        Validamos acá en vez de dejar fallar al SDK porque:
        - Ahorra un round-trip HTTP para errores obvios.
        - El mensaje de error es más claro que el `400` que devuelve Anthropic.
        - Es responsabilidad del adapter sanitizar input mal formado del grafo.
        """
        if not messages:
            raise ValueError("messages no puede estar vacía")
        system_parts: list[str] = []
        chat: list[dict[str, str]] = []
        for m in messages:
            if m.role not in _VALID_ROLES:
                raise ValueError(f"role inválido: {m.role!r}")
            if m.role == _ROLE_SYSTEM:
                system_parts.append(m.content)
            else:
                chat.append({"role": m.role, "content": m.content})
        if not chat:
            raise ValueError(
                "se necesita al menos un mensaje user/assistant (Anthropic rechaza system-only)"
            )
        system_block = "\n\n".join(system_parts) if system_parts else None
        return system_block, chat


# ===========================================================================
# Conversión de eventos SDK → LlmStreamEvent
# ===========================================================================


def _convert_event(event: Any) -> LlmStreamEvent | None:
    """Mapea un evento del Anthropic SDK a nuestro `LlmStreamEvent`.

    Devuelve `None` para eventos que no nos interesan emitir hacia el
    grafo (message_start, message_stop, ping, etc.). El evento `stop`
    real lo emitimos manualmente desde `stream()` con el usage final.
    """
    event_type = getattr(event, "type", "")

    if event_type == "content_block_delta":
        delta = getattr(event, "delta", None)
        if delta is None:
            return None
        delta_type = getattr(delta, "type", "")
        if delta_type == "text_delta":
            return LlmStreamEvent(
                kind="text",
                payload={"delta": getattr(delta, "text", "")},
            )
        if delta_type == "input_json_delta":
            # Streaming de inputs de tool use — el caller acumula y emite
            # tool-use cuando se cierra el bloque.
            return LlmStreamEvent(
                kind="tool_use_delta",
                payload={"delta": getattr(delta, "partial_json", "")},
            )

    if event_type == "content_block_start":
        block = getattr(event, "content_block", None)
        if block is None:
            return None
        if getattr(block, "type", "") == "tool_use":
            return LlmStreamEvent(
                kind="tool_use_start",
                payload={
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                },
            )

    return None


# ===========================================================================
# Extracción de usage del response completo
# ===========================================================================


def _extract_text(message: AnthropicMessage) -> str:
    """Concatena los bloques de texto del response. Ignora tool_use blocks."""
    parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", "") == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts)


def _extract_usage(message: AnthropicMessage) -> dict[str, int]:
    """Lee el `usage` del response y normaliza nombres. Anthropic devuelve
    None cuando no aplica (sin caching), lo tratamos como 0.
    """
    usage = message.usage
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }
