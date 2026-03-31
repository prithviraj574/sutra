"""add_runtime_host_fields_and_jobs

Revision ID: d9d22635b1d4
Revises: ab4e1c9d2f73
Create Date: 2026-03-31 21:10:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401


# revision identifiers, used by Alembic.
revision = "d9d22635b1d4"
down_revision = "ab4e1c9d2f73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runtime_leases",
        sa.Column("host_vm_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "runtime_leases",
        sa.Column("host_api_base_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index(
        op.f("ix_runtime_leases_host_vm_id"),
        "runtime_leases",
        ["host_vm_id"],
        unique=False,
    )

    op.create_table(
        "automation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("schedule", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("prompt", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_automation_jobs_agent_id"), "automation_jobs", ["agent_id"], unique=False)
    op.create_index(op.f("ix_automation_jobs_id"), "automation_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_automation_jobs_team_id"), "automation_jobs", ["team_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_automation_jobs_team_id"), table_name="automation_jobs")
    op.drop_index(op.f("ix_automation_jobs_id"), table_name="automation_jobs")
    op.drop_index(op.f("ix_automation_jobs_agent_id"), table_name="automation_jobs")
    op.drop_table("automation_jobs")

    op.drop_index(op.f("ix_runtime_leases_host_vm_id"), table_name="runtime_leases")
    op.drop_column("runtime_leases", "host_api_base_url")
    op.drop_column("runtime_leases", "host_vm_id")
