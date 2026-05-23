"""DevTokenValidator — adapter de auth para entornos locales.

Acepta tokens de la forma `dev:{oid}` donde `{oid}` es el Entra Object ID
que el frontend stub MSAL emite (formato `stub-{roleId}-00000000` por
defecto, ver `lib/auth/auth-stub.ts` en el frontend).

Validaciones:
1. Solo activable cuando `app_env ∈ {dev, test}`. En staging/prod
   `validate()` lanza `UnauthorizedError` siempre — defensa en profundidad
   contra una mala configuración que deje el provider expuesto.
2. El token debe empezar con `dev:` exactamente.
3. El `oid` debe existir en la tabla `users` (sembrada por
   `adapters/repositories/postgres/seed.py`). Si no existe, `resolve_user`
   lanza `UnauthorizedError` en lugar de auto-crear — los usuarios reales
   se crean al login con Entra ID (1B-azure).
"""

from __future__ import annotations

from sqa_kb.config import AppEnv
from sqa_kb.domain.entities import User
from sqa_kb.domain.errors import UnauthorizedError
from sqa_kb.ports.gateways import TokenClaims
from sqa_kb.ports.repositories import UserRepository

DEV_PREFIX = "dev:"


class DevTokenValidator:
    """Acepta tokens `dev:{oid}` mapeando contra usuarios sembrados."""

    def __init__(self, user_repo: UserRepository, *, app_env: AppEnv) -> None:
        self._user_repo = user_repo
        self._app_env = app_env

    @property
    def is_enabled(self) -> bool:
        """True solo en dev/test."""
        return self._app_env in (AppEnv.DEV, AppEnv.TEST)

    async def validate(self, bearer_token: str) -> TokenClaims:
        if not self.is_enabled:
            raise UnauthorizedError(
                "DevTokenValidator está deshabilitado en este entorno"
            )

        token = (bearer_token or "").strip()
        if not token.startswith(DEV_PREFIX):
            raise UnauthorizedError("Token no reconocido por el provider local")

        oid = token[len(DEV_PREFIX) :].strip()
        if not oid:
            raise UnauthorizedError("Token vacío después del prefijo `dev:`")

        # Consultamos el repo para hidratar email + name. Si el oid no está
        # sembrado, el resolve falla más tarde — preferimos esto a auto-crear,
        # que oculta el problema y desvía del contrato con Entra ID.
        user = await self._user_repo.get_by_oid(oid)
        if user is None:
            raise UnauthorizedError(
                f"OID {oid!r} no existe en `users`. Corré "
                "`python -m sqa_kb.adapters.repositories.postgres.seed`."
            )

        return TokenClaims(
            oid=user.oid,
            email=user.email,
            name=user.name,
            groups=(),
        )

    async def resolve_user(self, claims: TokenClaims) -> User:
        user = await self._user_repo.get_by_oid(claims.oid)
        if user is None:
            raise UnauthorizedError(
                f"OID {claims.oid!r} no existe en `users`"
            )
        return user
