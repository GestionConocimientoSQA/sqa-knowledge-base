"""Tests de integración del endpoint POST /sessions/{id}/messages.

Requieren DB (sesión real) y un fake graph inyectado en app.state para
no necesitar Anthropic real.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sqa_kb.adapters.repositories.postgres.seed import seed
from sqa_kb.api.sse import SseEventBuffer
from sqa_kb.main import create_app

CAPTURADOR = "Bearer dev:stub-capturador-00000000"
OWNER = "Bearer dev:stub-owner-00000000"


# ===========================================================================
# Fake graph (mismo shape que el orchestrator usa)
# ===========================================================================


@dataclass
class _FakeStateSnapshot:
    values: dict[str, Any]


@dataclass
class _FakeGraph:
    """Imita la API mínima usada por el orchestrator."""

    state_sequence: list[dict[str, Any]] = field(default_factory=list)

    async def aget_state(self, config: dict[str, Any]) -> _FakeStateSnapshot:
        return _FakeStateSnapshot(values={})

    def astream(
        self,
        input_payload: dict[str, Any] | None,
        config: dict[str, Any],
        stream_mode: str = "values",
    ) -> AsyncIterator[dict[str, Any]]:
        outer = self

        async def gen() -> AsyncIterator[dict[str, Any]]:
            for state in outer.state_sequence:
                yield state

        return gen()


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(scope="module")
async def _seeded(session_factory) -> None:  # type: ignore[no-untyped-def]
    await seed(session_factory)


@pytest.fixture
def client_with_fake_graph(_seeded) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    """TestClient con un fake graph que emite 2 estados (stage + texto)."""
    app = create_app()
    fake_graph = _FakeGraph(
        state_sequence=[
            {"current_stage": "ETAPA_0"},
            {
                "current_stage": "ETAPA_0",
                "messages": [
                    {
                        "role": "agent",
                        "content": "Hola del agente",
                        "stage": "ETAPA_0",
                    }
                ],
            },
        ],
    )
    app.state.agent_graph = fake_graph
    app.state.sse_buffer = SseEventBuffer()
    with TestClient(app) as c:
        yield c


# ===========================================================================
# Auth + IDOR
# ===========================================================================


def test_post_without_bearer_returns_401(client_with_fake_graph: TestClient) -> None:
    """Sin bearer header → 401."""
    response = client_with_fake_graph.post(
        "/sessions/some-id/messages",
        json={"content": "hola"},
    )
    assert response.status_code == 401


def test_post_to_unknown_session_returns_404(
    client_with_fake_graph: TestClient,
) -> None:
    response = client_with_fake_graph.post(
        "/sessions/never-existed-99/messages",
        headers={"Authorization": CAPTURADOR},
        json={"content": "hola"},
    )
    assert response.status_code == 404


def test_post_to_other_users_session_returns_404(
    client_with_fake_graph: TestClient,
) -> None:
    """IDOR: Owner crea sesión, Capturador no la puede ver → 404."""
    created = client_with_fake_graph.post(
        "/sessions",
        headers={"Authorization": OWNER},
        json={"mode": "captura"},
    ).json()

    response = client_with_fake_graph.post(
        f"/sessions/{created['id']}/messages",
        headers={"Authorization": CAPTURADOR},
        json={"content": "hola"},
    )
    assert response.status_code == 404


# ===========================================================================
# Happy path SSE
# ===========================================================================


def test_post_returns_sse_content_type(client_with_fake_graph: TestClient) -> None:
    created = client_with_fake_graph.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    with client_with_fake_graph.stream(
        "POST",
        f"/sessions/{created['id']}/messages",
        headers={"Authorization": CAPTURADOR},
        json={"content": "hola"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache, no-transform"
        assert response.headers["x-accel-buffering"] == "no"


def test_post_streams_message_start_and_end(
    client_with_fake_graph: TestClient,
) -> None:
    created = client_with_fake_graph.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    with client_with_fake_graph.stream(
        "POST",
        f"/sessions/{created['id']}/messages",
        headers={"Authorization": CAPTURADOR},
        json={"content": "hola"},
    ) as response:
        body = b"".join(response.iter_bytes())

    text = body.decode("utf-8")
    assert "event: message-start" in text
    assert "event: message-end" in text


def test_post_streams_text_delta_for_agent_message(
    client_with_fake_graph: TestClient,
) -> None:
    created = client_with_fake_graph.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    with client_with_fake_graph.stream(
        "POST",
        f"/sessions/{created['id']}/messages",
        headers={"Authorization": CAPTURADOR},
        json={"content": "hola"},
    ) as response:
        body = b"".join(response.iter_bytes())

    text = body.decode("utf-8")
    assert "event: text-delta" in text
    assert "Hola del agente" in text


def test_post_validates_content_length(
    client_with_fake_graph: TestClient,
) -> None:
    """content vacío → 422 (Pydantic min_length=1)."""
    created = client_with_fake_graph.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    response = client_with_fake_graph.post(
        f"/sessions/{created['id']}/messages",
        headers={"Authorization": CAPTURADOR},
        json={"content": ""},
    )
    assert response.status_code == 422


# ===========================================================================
# Last-Event-ID
# ===========================================================================


def test_post_accepts_last_event_id_header(
    client_with_fake_graph: TestClient,
) -> None:
    """Header Last-Event-ID parsea sin romper aunque no haya buffered events."""
    created = client_with_fake_graph.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    with client_with_fake_graph.stream(
        "POST",
        f"/sessions/{created['id']}/messages",
        headers={
            "Authorization": CAPTURADOR,
            "Last-Event-ID": "5",
        },
        json={"content": "hola"},
    ) as response:
        assert response.status_code == 200
        # Sin eventos buffered antes del id=5 → solo emite los nuevos.
        body = b"".join(response.iter_bytes())
        assert b"event: message-start" in body


def test_post_ignores_invalid_last_event_id(
    client_with_fake_graph: TestClient,
) -> None:
    """Header corrupto (no numérico) no debe fallar el request."""
    created = client_with_fake_graph.post(
        "/sessions",
        headers={"Authorization": CAPTURADOR},
        json={"mode": "captura"},
    ).json()

    with client_with_fake_graph.stream(
        "POST",
        f"/sessions/{created['id']}/messages",
        headers={
            "Authorization": CAPTURADOR,
            "Last-Event-ID": "not-a-number",
        },
        json={"content": "hola"},
    ) as response:
        assert response.status_code == 200
