from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260616_0003"
down_revision = "20260616_0002"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    columns = _columns("users")

    if "provider" not in columns:
        op.add_column("users", sa.Column("provider", sa.String(length=20), nullable=True))

    if "provider_id" not in columns:
        op.add_column("users", sa.Column("provider_id", sa.String(length=100), nullable=True))

    if "ix_users_provider_id" not in _indexes("users"):
        op.create_index("ix_users_provider_id", "users", ["provider_id"], unique=False)


def downgrade() -> None:
    columns = _columns("users")

    if "ix_users_provider_id" in _indexes("users"):
        op.drop_index("ix_users_provider_id", table_name="users")

    if "provider_id" in columns:
        op.drop_column("users", "provider_id")

    if "provider" in columns:
        op.drop_column("users", "provider")
