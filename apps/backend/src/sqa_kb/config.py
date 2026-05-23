"""App configuration via Pydantic Settings (12-factor).

Toda la configuración runtime viene de env vars con prefijo `SQA_KB_`.
Las decisiones de stack pendientes con TI (PostgreSQL vs Azure SQL,
LiteLLM endpoint, etc.) se expresan como vars que aceptan ambos valores
— el adapter concreto en `adapters/` resuelve cuál usar.

Cargar `.env` automáticamente solo en `dev` y `test`. En staging/prod los
valores vienen de Azure Key Vault inyectados por Container Apps.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Self

from pydantic import AnyUrl, BeforeValidator, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_csv_list(v: object) -> object:
    """Convierte un string CSV a list[str]. Tolera ya-listas."""
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return v


# Tipo reusable: list[str] que acepta CSV desde env vars.
# `NoDecode` apaga el JSON parser default de pydantic-settings para que
# el `BeforeValidator` reciba el string crudo y lo split por comas.
CsvList = Annotated[list[str], NoDecode, BeforeValidator(_parse_csv_list)]


class AppEnv(StrEnum):
    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"


class DatabaseDialect(StrEnum):
    """Stack de DB. **Decisión cerrada 2026-05-22**: PostgreSQL + pgvector
    en local y en Azure (Flexible Server). Azure SQL queda solo como
    placeholder histórico — no se implementa adapter `azure_sql`. Si en
    un futuro lejano hubiera que migrar, el `database_url` + un segundo
    adapter alcanzan; no requiere cambiar dominio ni puertos.
    """

    POSTGRES = "postgres"
    AZURE_SQL = "azure_sql"  # no soportado, ver docstring.


class VectorStore(StrEnum):
    """Vector store. Default `none` para Fase 1A (sin RAG todavía)."""

    NONE = "none"
    PGVECTOR = "pgvector"
    AZURE_AI_SEARCH = "azure_ai_search"


class LlmGatewayKind(StrEnum):
    """Cómo se habla con Claude. Decisión TI pendiente."""

    ANTHROPIC_DIRECT = "anthropic_direct"
    LITELLM = "litellm"


class Settings(BaseSettings):
    """Toda la config runtime. Prefijo `SQA_KB_` para todas las vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SQA_KB_",
        extra="ignore",
        str_strip_whitespace=True,
    )

    # ---------------- App ----------------

    app_env: AppEnv = Field(default=AppEnv.DEV)
    app_name: str = Field(default="sqa-kb-backend")
    api_v1_prefix: str = Field(default="/api/v1")

    # ---------------- CORS ----------------

    cors_allowed_origins: CsvList = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Lista separada por comas en env. Frontend dev + staging + prod.",
    )

    # ---------------- Database ----------------

    database_dialect: DatabaseDialect = Field(default=DatabaseDialect.POSTGRES)
    """Decisión pendiente con TI. Default `postgres` para no romper compose local."""

    database_url: SecretStr | None = Field(default=None)
    """DSN async. Postgres: `postgresql+asyncpg://...`. Azure SQL: `mssql+aioodbc://...`.
    None en `test` (los tests usan fakes de repositorio)."""

    database_echo: bool = Field(default=False)
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_pool_max_overflow: int = Field(default=20, ge=0, le=200)

    # ---------------- Auth (Microsoft Entra ID) ----------------

    entra_tenant_id: str | None = Field(default=None)
    entra_client_id: str | None = Field(default=None)
    entra_api_audience: str | None = Field(
        default=None,
        description='Application ID URI del backend (ej: "api://sqa-kb").',
    )
    entra_jwks_cache_ttl_seconds: int = Field(default=3600, ge=60)

    # ---------------- Azure resources ----------------

    azure_blob_account_url: AnyUrl | None = Field(default=None)
    azure_blob_container_documents: str = Field(default="documents")
    azure_blob_container_uploads: str = Field(default="uploads")
    azure_blob_container_artifacts: str = Field(default="artifacts")
    azure_storage_connection_string: SecretStr | None = Field(default=None)
    """En local (Azurite). En Azure se usa Managed Identity vía `blob_account_url`."""

    azure_key_vault_url: AnyUrl | None = Field(default=None)
    azure_app_insights_connection_string: SecretStr | None = Field(default=None)

    # ---------------- Vector store ----------------

    vector_store: VectorStore = Field(default=VectorStore.NONE)
    azure_ai_search_endpoint: AnyUrl | None = Field(default=None)
    azure_ai_search_api_key: SecretStr | None = Field(default=None)
    azure_ai_search_index: str = Field(default="kb-chunks")

    # ---------------- LLM gateway ----------------

    llm_gateway_kind: LlmGatewayKind = Field(default=LlmGatewayKind.ANTHROPIC_DIRECT)
    anthropic_api_key: SecretStr | None = Field(default=None)
    """Solo si `llm_gateway_kind=anthropic_direct`."""
    litellm_base_url: AnyUrl | None = Field(default=None)
    litellm_api_key: SecretStr | None = Field(default=None)
    """Solo si `llm_gateway_kind=litellm` (proxy gestionado por TI o self-host)."""

    llm_default_model: str = Field(default="claude-sonnet-4-6")
    llm_classification_model: str = Field(default="claude-haiku-4")
    llm_deep_model: str = Field(default="claude-opus-4")

    # ---------------- PII / anonymization (Presidio) ----------------

    presidio_enabled: bool = Field(default=False)
    presidio_endpoint: AnyUrl | None = Field(default=None)

    # ---------------- Observability ----------------

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)
    """En dev local podés setear false para output legible en consola."""
    otel_exporter_otlp_endpoint: AnyUrl | None = Field(default=None)

    # ---------------- Workers / queue ----------------

    redis_url: SecretStr | None = Field(default=None)
    """Para arq workers (indexer, ingestion_processor) — Fase 3/4."""

    # ---------------- Validation ----------------

    @model_validator(mode="after")
    def _validate_combinations(self) -> Self:
        if self.app_env in (AppEnv.STAGING, AppEnv.PROD):
            # En prod/staging exigimos los pilares de identidad — fail fast.
            missing: list[str] = []
            if not self.entra_tenant_id:
                missing.append("SQA_KB_ENTRA_TENANT_ID")
            if not self.entra_client_id:
                missing.append("SQA_KB_ENTRA_CLIENT_ID")
            if not self.database_url:
                missing.append("SQA_KB_DATABASE_URL")
            if missing:
                raise ValueError(
                    f"Faltan vars obligatorias en {self.app_env.value}: {', '.join(missing)}"
                )

        if (
            self.llm_gateway_kind is LlmGatewayKind.ANTHROPIC_DIRECT
            and self.app_env in (AppEnv.STAGING, AppEnv.PROD)
            and not self.anthropic_api_key
        ):
            raise ValueError(
                "SQA_KB_ANTHROPIC_API_KEY es obligatoria con llm_gateway_kind=anthropic_direct."
            )

        if self.llm_gateway_kind is LlmGatewayKind.LITELLM and not self.litellm_base_url:
            raise ValueError("SQA_KB_LITELLM_BASE_URL es obligatoria con LiteLLM.")

        return self

    @property
    def is_local(self) -> bool:
        return self.app_env in (AppEnv.DEV, AppEnv.TEST)


@lru_cache
def get_settings() -> Settings:
    """Singleton lazy — importable desde cualquier módulo sin overhead."""
    return Settings()
