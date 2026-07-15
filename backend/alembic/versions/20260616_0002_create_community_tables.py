from __future__ import annotations

from alembic import op

revision = "20260616_0002"
down_revision = "20260609_0001"
branch_labels = None
depends_on = None


COMMUNITY_TABLES = [
    "community_posts",
    "community_comments",
    "community_translations",
    "community_reactions",
    "community_reports",
]


def upgrade() -> None:
    bind = op.get_bind()

    from app import models

    for table_name in COMMUNITY_TABLES:
        models.Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()

    from app import models

    for table_name in reversed(COMMUNITY_TABLES):
        models.Base.metadata.tables[table_name].drop(bind, checkfirst=True)
