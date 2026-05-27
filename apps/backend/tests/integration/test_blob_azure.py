"""Tests de integración del AzureBlobStorage contra Azurite (Fase 4.6).

Requieren Azurite corriendo (`docker compose up azurite`). Si no está
disponible, los tests se skipean (no fallan) — mismo patrón que los
tests de PostgreSQL.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

from sqa_kb.adapters.blob import AzureBlobStorage

# Connection string del emulador Azurite (account key pública de Microsoft,
# documentada — no es un secreto). Override por env var si Azurite corre
# en otro host/puerto.
AZURITE_CONN = os.environ.get(
    "SQA_KB_AZURITE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEhibT2EMV6Hod2qWmGXOZAH7sHpV/"
    "jVQYUbqHdK4xJk6Q/EOPpJjMfBR2cMo3w==;"
    "BlobEndpoint=http://localhost:10000/devstoreaccount1;",
)

TEST_CONTAINER = "test-ingesta"


@pytest_asyncio.fixture
async def blob() -> AzureBlobStorage:
    """Adapter contra Azurite. Skipea si Azurite no responde."""
    storage = AzureBlobStorage(connection_string=AZURITE_CONN)
    # Smoke: intentar un upload mínimo para detectar disponibilidad.
    probe_path = f"_probe/{uuid.uuid4().hex}.txt"
    try:
        await storage.upload(
            container=TEST_CONTAINER,
            path=probe_path,
            data=b"probe",
            content_type="text/plain",
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Azurite no disponible: {exc}")
    await storage.delete(container=TEST_CONTAINER, path=probe_path)
    return storage


async def test_upload_download_roundtrip(blob: AzureBlobStorage) -> None:
    path = f"{uuid.uuid4().hex}/doc.bin"
    payload = b"contenido binario de prueba \x00\x01\x02"
    meta = await blob.upload(
        container=TEST_CONTAINER,
        path=path,
        data=payload,
        content_type="application/octet-stream",
    )
    assert meta.path == path
    assert meta.size_bytes == len(payload)
    assert meta.etag

    downloaded = await blob.download(container=TEST_CONTAINER, path=path)
    assert downloaded == payload

    await blob.delete(container=TEST_CONTAINER, path=path)


async def test_upload_overwrites(blob: AzureBlobStorage) -> None:
    path = f"{uuid.uuid4().hex}/over.bin"
    await blob.upload(
        container=TEST_CONTAINER, path=path, data=b"v1", content_type="text/plain"
    )
    await blob.upload(
        container=TEST_CONTAINER, path=path, data=b"v2-mas-largo", content_type="text/plain"
    )
    assert await blob.download(container=TEST_CONTAINER, path=path) == b"v2-mas-largo"
    await blob.delete(container=TEST_CONTAINER, path=path)


async def test_delete_is_idempotent(blob: AzureBlobStorage) -> None:
    """Borrar un blob inexistente no debe fallar."""
    await blob.delete(container=TEST_CONTAINER, path=f"{uuid.uuid4().hex}/noexiste.bin")


async def test_signed_url_with_connection_string(blob: AzureBlobStorage) -> None:
    path = f"{uuid.uuid4().hex}/signed.bin"
    await blob.upload(
        container=TEST_CONTAINER, path=path, data=b"x", content_type="text/plain"
    )
    url = await blob.signed_url(container=TEST_CONTAINER, path=path)
    assert TEST_CONTAINER in url
    assert path in url
    assert "sig=" in url  # el SAS incluye la firma
    await blob.delete(container=TEST_CONTAINER, path=path)


def test_constructor_requires_some_auth() -> None:
    with pytest.raises(ValueError, match="connection_string"):
        AzureBlobStorage()


async def test_signed_url_managed_identity_not_implemented() -> None:
    storage = AzureBlobStorage(account_url="https://x.blob.core.windows.net")
    with pytest.raises(NotImplementedError):
        await storage.signed_url(container="c", path="p")
