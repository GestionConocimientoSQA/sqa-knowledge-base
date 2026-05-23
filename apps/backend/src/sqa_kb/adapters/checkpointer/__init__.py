"""Adapter de checkpointer para LangGraph.

Usa `AsyncPostgresSaver` del paquete oficial `langgraph-checkpoint-postgres`
en lugar de una implementación propia (ver IMPLEMENTATION-STATUS Fase 2.1
para la decisión).

Tablas creadas por la primera ejecución de `setup()`:
- `checkpoint_migrations` — versionado interno de LangGraph.
- `checkpoints` — snapshot del state por (thread_id, ns, checkpoint_id).
- `checkpoint_writes` — writes pendientes en medio de un step.
- `checkpoint_blobs` — payloads grandes referenciados por channel/version.

Estas tablas viven aparte del schema del dominio. NO se cruzan con
`sessions` ni `messages` del dominio — el `thread_id` que LangGraph
maneja es el `session_id` del dominio (link semántico, no FK).
"""

from sqa_kb.adapters.checkpointer.postgres import (
    CheckpointerBundle,
    build_checkpointer,
    psycopg_dsn,
)

__all__ = [
    "CheckpointerBundle",
    "build_checkpointer",
    "psycopg_dsn",
]
