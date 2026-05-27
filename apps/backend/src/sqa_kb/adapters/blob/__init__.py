"""Adapters de Blob Storage (Fase 4.6).

`AzureBlobStorage` implementa el puerto `BlobStorage` usando
`azure-storage-blob`:
- En local: Azurite vía connection string.
- En Azure: Managed Identity vía `account_url` + `DefaultAzureCredential`.
"""

from sqa_kb.adapters.blob.azure import AzureBlobStorage

__all__ = ["AzureBlobStorage"]
