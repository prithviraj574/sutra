"""add_team_task_updates

Revision ID: f1c4d3e9a8b6
Revises: e7db1f1b2a77
Create Date: 2026-03-31 00:16:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401


# revision identifiers, used by Alembic.
revision = "f1c4d3e9a8b6"
down_revision = "e7db1f1b2a77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_task_updates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["team_tasks.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_team_task_updates_id"), "team_task_updates", ["id"], unique=False)
    op.create_index(op.f("ix_team_task_updates_task_id"), "team_task_updates", ["task_id"], unique=False)
    op.create_index(op.f("ix_team_task_updates_team_id"), "team_task_updates", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_task_updates_agent_id"), "team_task_updates", ["agent_id"], unique=False)
    op.create_index(op.f("ix_team_task_updates_event_type"), "team_task_updates", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_team_task_updates_event_type"), table_name="team_task_updates")
    op.drop_index(op.f("ix_team_task_updates_agent_id"), table_name="team_task_updates")
    op.drop_index(op.f("ix_team_task_updates_team_id"), table_name="team_task_updates")
    op.drop_index(op.f("ix_team_task_updates_task_id"), table_name="team_task_updates")
    op.drop_index(op.f("ix_team_task_updates_id"), table_name="team_task_updates")
    op.drop_table("team_task_updates")
