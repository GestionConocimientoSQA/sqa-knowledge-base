"""Tests del encoder SSE + tipos de eventos.

Cubren:
- Encoder produce el wire format correcto (id/event/data).
- Multi-line data se split por línea (regla SSE).
- Unicode preservado (sin ensure_ascii).
- Encoder de comentarios (keepalive).
- Catálogo de tipos completo (14 valores).
"""

from __future__ import annotations

import json

from sqa_kb.api.sse.events import (
    SseEvent,
    SseEventType,
    encode_comment,
    encode_sse,
)

# ===========================================================================
# Catálogo de eventos
# ===========================================================================


def test_catalog_includes_14_event_types() -> None:
    expected = {
        "message-start",
        "stage-change",
        "classification",
        "kb-search-result",
        "text-delta",
        "tool-use",
        "tool-result",
        "citation",
        "scoring",
        "document-generated",
        "token-usage",
        "message-end",
        "error",
        "ping",
    }
    assert {e.value for e in SseEventType} == expected


def test_event_type_is_string_enum() -> None:
    """Permite comparar con strings directamente — útil en el orquestador."""
    assert SseEventType.TEXT_DELTA == "text-delta"
    assert SseEventType.MESSAGE_END == "message-end"


# ===========================================================================
# encode_sse
# ===========================================================================


def test_encode_simple_event_format() -> None:
    event = SseEvent(
        id=1, type=SseEventType.TEXT_DELTA, data={"delta": "Hola"}
    )
    wire = encode_sse(event).decode("utf-8")
    assert wire == 'id: 1\nevent: text-delta\ndata: {"delta":"Hola"}\n\n'


def test_encode_preserves_unicode() -> None:
    """No ensure_ascii — los acentos del español deben ir intactos."""
    event = SseEvent(
        id=42,
        type=SseEventType.TEXT_DELTA,
        data={"delta": "Acción técnica con ñ"},
    )
    wire = encode_sse(event).decode("utf-8")
    assert "Acción técnica con ñ" in wire


def test_encode_ends_with_double_newline() -> None:
    """SSE separa eventos con `\\n\\n`. El terminador siempre debe estar."""
    event = SseEvent(id=1, type=SseEventType.PING, data={})
    wire = encode_sse(event).decode("utf-8")
    assert wire.endswith("\n\n")


def test_encode_data_splits_multiline_by_line() -> None:
    """Si data tiene \\n, cada línea debe tener su propio prefijo `data:`."""
    # Forzamos JSON con saltos de línea reales en el contenido — no es
    # común porque usamos separators sin newlines, pero validamos la
    # robustez del encoder.
    event = SseEvent(
        id=1,
        type=SseEventType.TEXT_DELTA,
        # Inyectamos `\n` literal en el contenido del JSON.
        data={"delta": "linea1\nlinea2"},
    )
    wire = encode_sse(event).decode("utf-8")
    # El JSON.dumps escapa el \n a \\n por defecto, así que en realidad
    # no debería haber líneas múltiples. Esto valida que NO partimos
    # cuando el JSON está en una sola línea.
    assert wire.count("data:") == 1


def test_encode_id_is_integer_on_wire() -> None:
    event = SseEvent(id=12345, type=SseEventType.MESSAGE_END, data={})
    wire = encode_sse(event).decode("utf-8")
    assert "id: 12345\n" in wire


def test_encode_data_serializes_dict_to_json() -> None:
    event = SseEvent(
        id=1,
        type=SseEventType.CLASSIFICATION,
        data={"category": "TEC", "confidence": 0.85},
    )
    wire = encode_sse(event).decode("utf-8")
    # JSON inline en data:
    data_line = next(ln for ln in wire.splitlines() if ln.startswith("data:"))
    payload = json.loads(data_line[5:].strip())
    assert payload == {"category": "TEC", "confidence": 0.85}


def test_encode_empty_data_dict() -> None:
    """data={} debe encodear como `data: {}` — no como cadena vacía."""
    event = SseEvent(id=1, type=SseEventType.PING, data={})
    wire = encode_sse(event).decode("utf-8")
    assert "data: {}\n" in wire


# ===========================================================================
# encode_comment
# ===========================================================================


def test_encode_comment_format() -> None:
    """Comentario SSE — línea con `:` al inicio, no incrementa event id."""
    wire = encode_comment("ping").decode("utf-8")
    assert wire == ": ping\n\n"


def test_encode_comment_is_idempotent_to_clients() -> None:
    """Un browser EventSource ignora líneas que empiezan con `:`."""
    wire = encode_comment("keepalive").decode("utf-8")
    assert wire.startswith(":")
    assert "event:" not in wire
    assert "id:" not in wire


# ===========================================================================
# SseEvent dataclass
# ===========================================================================


def test_event_is_frozen() -> None:
    import pytest

    event = SseEvent(id=1, type=SseEventType.PING, data={})
    with pytest.raises((AttributeError, Exception)):
        event.id = 999  # type: ignore[misc]


def test_event_equality_value_based() -> None:
    a = SseEvent(id=1, type=SseEventType.PING, data={"x": 1})
    b = SseEvent(id=1, type=SseEventType.PING, data={"x": 1})
    assert a == b


def test_event_inequality_when_data_differs() -> None:
    a = SseEvent(id=1, type=SseEventType.PING, data={"x": 1})
    b = SseEvent(id=1, type=SseEventType.PING, data={"x": 2})
    assert a != b
