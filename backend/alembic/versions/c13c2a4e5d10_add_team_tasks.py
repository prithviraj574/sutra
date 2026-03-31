"""add_team_tasks

Revision ID: c13c2a4e5d10
Revises: 6f8b1f0b6c2a
Create Date: 2026-03-30 23:35:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401


# revision identifiers, used by Alembic.
revision = "c13c2a4e5d10"
down_revision = "6f8b1f0b6c2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_agent_id", sa.Uuid(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("instruction", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_team_tasks_id"), "team_tasks", ["id"], unique=False)
    op.create_index(
        op.f("ix_team_tasks_assigned_agent_id"),
        "team_tasks",
        ["assigned_agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_team_tasks_conversation_id"),
        "team_tasks",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_team_tasks_status"), "team_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_team_tasks_source"), "team_tasks", ["source"], unique=False)
    op.create_index(op.f("ix_team_tasks_team_id"), "team_tasks", ["team_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_team_tasks_team_id"), table_name="team_tasks")
    op.drop_index(op.f("ix_team_tasks_source"), table_name="team_tasks")
    op.drop_index(op.f("ix_team_tasks_status"), table_name="team_tasks")
    op.drop_index(op.f("ix_team_tasks_conversation_id"), table_name="team_tasks")
    op.drop_index(op.f("ix_team_tasks_assigned_agent_id"), table_name="team_tasks")
    op.drop_index(op.f("ix_team_tasks_id"), table_name="team_tasks")
    op.drop_table("team_tasks")
