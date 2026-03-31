"""add_team_task_claim_fields

Revision ID: e7db1f1b2a77
Revises: c13c2a4e5d10
Create Date: 2026-03-30 23:58:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7db1f1b2a77"
down_revision = "c13c2a4e5d10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "team_tasks",
        sa.Column("claim_token", sa.String(), nullable=True),
    )
    op.add_column(
        "team_tasks",
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "team_tasks",
        sa.Column("claim_expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_team_tasks_claim_token"),
        "team_tasks",
        ["claim_token"],
        unique=False,
    )
    op.create_index(
        op.f("ix_team_tasks_claim_expires_at"),
        "team_tasks",
        ["claim_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_team_tasks_claim_expires_at"), table_name="team_tasks")
    op.drop_index(op.f("ix_team_tasks_claim_token"), table_name="team_tasks")
    op.drop_column("team_tasks", "claim_expires_at")
    op.drop_column("team_tasks", "claimed_at")
    op.drop_column("team_tasks", "claim_token")
