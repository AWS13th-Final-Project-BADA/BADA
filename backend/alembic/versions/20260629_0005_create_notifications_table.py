"""Create notifications table.

Revision ID: 20260629_0005
Revises: 20260616_0004
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260629_0005"
down_revision = "20260616_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("notifications")
