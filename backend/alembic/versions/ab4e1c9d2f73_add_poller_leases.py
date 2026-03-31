"""add_poller_leases

Revision ID: ab4e1c9d2f73
Revises: f1c4d3e9a8b6
Create Date: 2026-03-31 00:55:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401


# revision identifiers, used by Alembic.
revision = "ab4e1c9d2f73"
down_revision = "f1c4d3e9a8b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "poller_leases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("owner_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_sweep_started_at", sa.DateTime(), nullable=True),
        sa.Column("last_sweep_completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_executed_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_poller_leases_name"),
    )
    op.create_index(op.f("ix_poller_leases_id"), "poller_leases", ["id"], unique=False)
    op.create_index(op.f("ix_poller_leases_name"), "poller_leases", ["name"], unique=False)
    op.create_index(op.f("ix_poller_leases_owner_id"), "poller_leases", ["owner_id"], unique=False)
    op.create_index(op.f("ix_poller_leases_state"), "poller_leases", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_poller_leases_state"), table_name="poller_leases")
    op.drop_index(op.f("ix_poller_leases_owner_id"), table_name="poller_leases")
    op.drop_index(op.f("ix_poller_leases_name"), table_name="poller_leases")
    op.drop_index(op.f("ix_poller_leases_id"), table_name="poller_leases")
    op.drop_table("poller_leases")
