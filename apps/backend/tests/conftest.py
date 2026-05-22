"""Fixtures comunes para pytest."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Aísla cada test del .env real del usuario.

    Limpia variables `SQA_KB_*` y fija `app_env=test` para que los tests
    no dependan del estado del archivo .env del developer.
    """
    for key in list(os.environ):
        if key.startswith("SQA_KB_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SQA_KB_APP_ENV", "test")
    # Reset del cache singleton del Settings entre tests.
    from sqa_kb import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()
