"""multi-tenant projects (Fase 9.1)

Introduce el modelo multi-tenant del KB:
  * Tabla `projects` (workspaces aislados con su propia base de conocimiento)
  * Tabla `project_members` (membresía + rol per-proyecto: project_owner | member)
  * Tablas `project_categories` / `project_doc_types` (taxonomía con override
    por proyecto sobre los catálogos globales)
  * Columna `project_id` (FK NOT NULL) en `documents`, `document_chunks`,
    `sessions`, `queries`, `ingestion_items`

Y migra los datos pre-existentes:
  * Crea proyecto seed `gk-general` (UUID fijo `00000000-0000-0000-0000-000000000001`)
    cuyo owner es el GK Lead del seed (`stub-gklead-00000000`).
  * Backfilea todas las filas existentes con ese `project_id`.
  * Migra el enum `users.role_id`:
        owner       → colaborador + membership `project_owner` en gk-general
        capturador  → colaborador + membership `member` en gk-general
        gklead      → gk_lead (sin membership; acceso por privilegio)
  * Pone NOT NULL a `project_id` después del backfill.

Notas operativas:
  - El backfill no usa batches porque la cardinalidad esperada al cierre
    de Fase 8 es baja (~10k chunks máximo). Cuando supere 100k, separar
    en chunks de UPDATE WHERE id BETWEEN ... LIMIT ... como dijimos en
    el ADR §Riesgos.
  - El downgrade es seguro pero destructivo: dropea todo lo nuevo y
    restaura el enum `role_id` antiguo. Las memberships y proyectos se
    pierden. No hay UNDO del backfill (los OIDs que estaban en `owner`
    quedan en `colaborador` después del downgrade).

Revision ID: d4f9a8e2b1c3
Revises: c8e2f5a1d3b6
Create Date: 2026-05-28 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f9a8e2b1c3"
down_revision: str | Sequence[str] | None = "c8e2f5a1d3b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# UUID determinístico del proyecto seed — referenciado también desde el
# código Python (`mappers.GK_GENERAL_PROJECT_ID`) y desde el seed.py.
# Mantener sincronizado si alguna vez se cambia (raro, dispara reindex
# completo del KB).
GK_GENERAL_PROJECT_ID = "00000000-0000-0000-0000-000000000001"
GK_LEAD_OID = "stub-gklead-00000000"


def upgrade() -> None:
    """Upgrade schema."""
    # ------------------------------------------------------------------
    # 1) Tablas nuevas (proyectos + memberships + taxonomía per-proyecto)
    # ------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "owner_oid",
            sa.String(length=128),
            sa.ForeignKey("users.oid"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_projects_slug"),
    )
    op.create_index("ix_projects_owner_oid", "projects", ["owner_oid"])

    op.create_table(
        "project_members",
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_oid",
            sa.String(length=128),
            sa.ForeignKey("users.oid", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_project_members_user_oid", "project_members", ["user_oid"])

    op.create_table(
        "project_categories",
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("code", sa.String(length=16), primary_key=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "parent_global_code",
            sa.String(length=16),
            sa.ForeignKey("categories.code"),
            nullable=True,
        ),
        sa.Column(
            "is_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "project_doc_types",
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("code", sa.String(length=16), primary_key=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "parent_global_code",
            sa.String(length=16),
            sa.ForeignKey("doc_types.code"),
            nullable=True,
        ),
        sa.Column(
            "is_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ------------------------------------------------------------------
    # 2) Asegurar que el GK Lead exista antes de crear el proyecto seed.
    #    En entornos vacíos (CI con DB fresca) los seed.py corre después
    #    de alembic upgrade head, así que el usuario puede no existir.
    #    Insertamos un placeholder idempotente que el seed luego enriquece.
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            INSERT INTO users (
                oid, email, name, role_id, carpetas_owned,
                puede_gobernar_taxonomia, puede_aprobar_taxonomia,
                puede_ver_metricas_globales
            )
            VALUES (
                :oid, :email, :name, 'gklead', '[]'::jsonb,
                true, true, true
            )
            ON CONFLICT (oid) DO NOTHING
            """
        ).bindparams(
            oid=GK_LEAD_OID,
            email="andres.altamiranda@sqa.co",
            name="Andrés Altamiranda",
        )
    )

    # ------------------------------------------------------------------
    # 3) Seed del proyecto gk-general y membership del GK Lead.
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            INSERT INTO projects (id, slug, name, description, owner_oid)
            VALUES (:id, :slug, :name, :description, :owner_oid)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            id=GK_GENERAL_PROJECT_ID,
            slug="gk-general",
            name="GK General",
            description=(
                "Proyecto raíz transversal de SQA Colombia. Aloja el "
                "conocimiento aplicable a toda la organización (no a un "
                "cliente puntual) y queda visible para todos los miembros."
            ),
            owner_oid=GK_LEAD_OID,
        )
    )

    # ------------------------------------------------------------------
    # 4) Agregar columna project_id a las 5 tablas existentes (nullable
    #    temporalmente), backfilear y poner NOT NULL después.
    # ------------------------------------------------------------------
    for table in ("documents", "document_chunks", "sessions", "queries", "ingestion_items"):
        op.add_column(
            table,
            sa.Column(
                "project_id",
                sa.String(length=36),
                sa.ForeignKey("projects.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        op.execute(
            sa.text(f"UPDATE {table} SET project_id = :pid").bindparams(
                pid=GK_GENERAL_PROJECT_ID
            )
        )
        op.alter_column(table, "project_id", nullable=False)
        op.create_index(f"ix_{table}_project_id", table, ["project_id"])

    # ------------------------------------------------------------------
    # 5) Migrar roles globales:
    #    - 'owner'      → 'colaborador' + membership project_owner en gk-general
    #    - 'capturador' → 'colaborador' + membership member en gk-general
    #    - 'gklead'     → sin cambios (no requiere membership)
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            INSERT INTO project_members (project_id, user_oid, role)
            SELECT :pid, oid,
                   CASE role_id
                       WHEN 'owner' THEN 'project_owner'
                       WHEN 'capturador' THEN 'member'
                   END
            FROM users
            WHERE role_id IN ('owner', 'capturador')
            ON CONFLICT DO NOTHING
            """
        ).bindparams(pid=GK_GENERAL_PROJECT_ID)
    )

    # Asegurar que el GK Lead también esté como owner del proyecto seed
    # (acceso explícito, además de su privilegio global).
    op.execute(
        sa.text(
            """
            INSERT INTO project_members (project_id, user_oid, role)
            VALUES (:pid, :oid, 'project_owner')
            ON CONFLICT DO NOTHING
            """
        ).bindparams(pid=GK_GENERAL_PROJECT_ID, oid=GK_LEAD_OID)
    )

    # Renombrar role_id en users de owner/capturador → colaborador.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role_id = 'colaborador'
            WHERE role_id IN ('owner', 'capturador')
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema — destructivo (pierde memberships y proyectos)."""
    # 1) Revertir role_id de colaborador → capturador (best-effort, no
    #    podemos distinguir cuáles eran owner originalmente).
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role_id = 'capturador'
            WHERE role_id = 'colaborador'
            """
        )
    )

    # 2) Quitar columna project_id de las 5 tablas.
    for table in ("ingestion_items", "queries", "sessions", "document_chunks", "documents"):
        op.drop_index(f"ix_{table}_project_id", table_name=table)
        op.drop_column(table, "project_id")

    # 3) Drop tablas nuevas (orden inverso por FKs).
    op.drop_table("project_doc_types")
    op.drop_table("project_categories")
    op.drop_index("ix_project_members_user_oid", table_name="project_members")
    op.drop_table("project_members")
    op.drop_index("ix_projects_owner_oid", table_name="projects")
    op.drop_table("projects")
