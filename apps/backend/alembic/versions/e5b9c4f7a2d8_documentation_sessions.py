"""documentation_sessions (Fase 9.5)

Crea la tabla `documentation_sessions` para persistir el state de las
sesiones guiadas que el `project_owner` corre con el agente durante el
onboarding de un proyecto. Cada sesión acumula respuestas por step y al
finalizar genera documentos `.md` que entran al pipeline de ingesta.

Schema:
- `id` UUID v4
- `project_id` FK → projects.id (CASCADE en delete del proyecto)
- `owner_oid` quien abrió la sesión
- `status` (in-progress | finalized | abandoned)
- `current_step` (context | taxonomy | sources | glossary | stakeholders)
- `step_data` JSONB con las respuestas acumuladas
- `started_at` / `finalized_at`
- `generated_document_ids` ARRAY de IDs de ingestion_items creados al
  finalizar — el `project_owner` los aprueba normalmente con la cola de
  ingesta.

Índices:
- `(project_id, status)` para listar sesiones activas por proyecto.
- `(owner_oid, started_at desc)` para "mis sesiones de doc".

Revision ID: e5b9c4f7a2d8
Revises: d4f9a8e2b1c3
Create Date: 2026-05-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5b9c4f7a2d8"
down_revision: str | None = "d4f9a8e2b1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documentation_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_oid", sa.String(128), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_step", sa.String(20), nullable=False),
        sa.Column(
            "step_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finalized_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "generated_document_ids",
            postgresql.ARRAY(sa.String(128)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
    )
    op.create_index(
        "ix_documentation_sessions_project_status",
        "documentation_sessions",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_documentation_sessions_owner",
        "documentation_sessions",
        ["owner_oid", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documentation_sessions_owner", table_name="documentation_sessions"
    )
    op.drop_index(
        "ix_documentation_sessions_project_status",
        table_name="documentation_sessions",
    )
    op.drop_table("documentation_sessions")
