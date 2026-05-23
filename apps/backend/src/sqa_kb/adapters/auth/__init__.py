"""Implementaciones del puerto `TokenValidator`.

- `dev.py` — acepta tokens fake del frontend stub MSAL. Solo activable
  cuando `app_env ∈ {dev, test}`. Resuelve el `User` consultando la
  `UserRepository` local.
- `entra.py` — placeholder para el adapter real con Entra ID (1B-azure),
  validará firma JWT contra JWKS y verificará claims `aud`, `iss`, `exp`, `oid`.
"""
