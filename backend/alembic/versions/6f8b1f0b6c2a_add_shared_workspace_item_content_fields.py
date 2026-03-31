"""add_shared_workspace_item_content_fields

Revision ID: 6f8b1f0b6c2a
Revises: 8e9091b03d62
Create Date: 2026-03-30 22:28:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6f8b1f0b6c2a"
down_revision = "8e9091b03d62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shared_workspace_items",
        sa.Column("content_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "shared_workspace_items",
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "shared_workspace_items",
        sa.Column("agent_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_shared_workspace_items_conversation_id_conversations"),
        "shared_workspace_items",
        "conversations",
        ["conversation_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_shared_workspace_items_agent_id_agents"),
        "shared_workspace_items",
        "agents",
        ["agent_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_shared_workspace_items_conversation_id"),
        "shared_workspace_items",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shared_workspace_items_agent_id"),
        "shared_workspace_items",
        ["agent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_shared_workspace_items_agent_id"), table_name="shared_workspace_items")
    op.drop_index(op.f("ix_shared_workspace_items_conversation_id"), table_name="shared_workspace_items")
    op.drop_constraint(
        op.f("fk_shared_workspace_items_agent_id_agents"),
        "shared_workspace_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_shared_workspace_items_conversation_id_conversations"),
        "shared_workspace_items",
        type_="foreignkey",
    )
    op.drop_column("shared_workspace_items", "agent_id")
    op.drop_column("shared_workspace_items", "conversation_id")
    op.drop_column("shared_workspace_items", "content_text")
