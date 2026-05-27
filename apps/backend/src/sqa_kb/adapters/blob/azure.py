"""AzureBlobStorage — adapter del puerto `BlobStorage` (Fase 4.6).

Implementa upload/download/delete/signed_url usando el SDK async de
`azure-storage-blob`. Dos modos de autenticación:

- **Local (Azurite)**: connection string (incluye la account key del
  emulador). `signed_url` genera un SAS con la account key.
- **Azure (prod)**: `account_url` + `DefaultAzureCredential` (Managed
  Identity). `signed_url` usa user-delegation SAS.

El adapter crea el container si no existe en el primer upload — así no
hace falta provisionarlos a mano en dev. En prod, Bicep los crea
(Fase 0/11) y el create-if-not-exists es no-op.

Cada operación abre y cierra su propio `BlobServiceClient` para evitar
problemas de event loop entre requests (mismo patrón defensivo que el
engine NullPool en tests). El overhead es despreciable comparado con la
latencia de red al Blob.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from azure.storage.blob import (
    BlobSasPermissions,
    generate_blob_sas,
)
from azure.storage.blob.aio import BlobServiceClient

from sqa_kb.ports.gateways import BlobMetadata


class AzureBlobStorage:
    """Adapter concreto de `BlobStorage`. Implementa el Protocol del puerto."""

    def __init__(
        self,
        *,
        connection_string: str | None = None,
        account_url: str | None = None,
    ) -> None:
        if not connection_string and not account_url:
            raise ValueError(
                "AzureBlobStorage requiere connection_string (Azurite) o "
                "account_url (Managed Identity)."
            )
        self._connection_string = connection_string
        self._account_url = account_url

    def _client(self) -> BlobServiceClient:
        if self._connection_string:
            return BlobServiceClient.from_connection_string(self._connection_string)
        # Managed Identity: import perezoso de azure-identity para no
        # cargarlo en local donde se usa connection string.
        from azure.identity.aio import DefaultAzureCredential

        return BlobServiceClient(
            account_url=self._account_url,  # type: ignore[arg-type]
            credential=DefaultAzureCredential(),
        )

    async def upload(
        self,
        *,
        container: str,
        path: str,
        data: bytes,
        content_type: str,
    ) -> BlobMetadata:
        import contextlib

        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import ContentSettings

        async with self._client() as client:
            container_client = client.get_container_client(container)
            with contextlib.suppress(ResourceExistsError):
                await container_client.create_container()
            blob_client = container_client.get_blob_client(path)
            await blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            props = await blob_client.get_blob_properties()
            return BlobMetadata(
                path=path,
                size_bytes=props.size,
                content_type=content_type,
                etag=str(props.etag),
            )

    async def download(self, *, container: str, path: str) -> bytes:
        async with self._client() as client:
            blob_client = client.get_blob_client(container=container, blob=path)
            stream = await blob_client.download_blob()
            return await stream.readall()

    async def delete(self, *, container: str, path: str) -> None:
        import contextlib

        from azure.core.exceptions import ResourceNotFoundError

        async with self._client() as client:
            blob_client = client.get_blob_client(container=container, blob=path)
            # Idempotente: borrar algo que no existe no es error.
            with contextlib.suppress(ResourceNotFoundError):
                await blob_client.delete_blob()

    async def signed_url(
        self,
        *,
        container: str,
        path: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Genera una URL temporal de lectura (SAS).

        Con connection string usa la account key. Con Managed Identity
        requeriría user-delegation SAS (no soportado en esta fase — en
        prod se usará `signed_url` solo si TI provee la key, o se sirve
        el blob vía el backend). Lanza `NotImplementedError` en modo MI.
        """
        if not self._connection_string:
            raise NotImplementedError(
                "signed_url con Managed Identity (user-delegation SAS) no "
                "implementado en Fase 4 — servir el blob vía backend."
            )
        async with self._client() as client:
            account_name = client.account_name
            account_key = self._extract_account_key()
            sas = generate_blob_sas(
                account_name=account_name,  # type: ignore[arg-type]
                container_name=container,
                blob_name=path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
            )
            base = client.url.rstrip("/")
            return f"{base}/{container}/{path}?{sas}"

    def _extract_account_key(self) -> str:
        """Extrae `AccountKey` de la connection string (para el SAS)."""
        cs = self._connection_string or ""
        for part in cs.split(";"):
            if part.startswith("AccountKey="):
                return part[len("AccountKey=") :]
        raise ValueError("La connection string no contiene AccountKey.")
