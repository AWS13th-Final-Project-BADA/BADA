from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260616_0004"
down_revision = "20260616_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE timeline_events "
            "ALTER COLUMN confidence TYPE VARCHAR(20) "
            "USING confidence::text"
        )
        return

    # SQLite smoke tests create the table from current SQLAlchemy metadata.
    # Altering column types in place would require batch-copying the table.


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        "ALTER TABLE timeline_events "
        "ALTER COLUMN confidence TYPE NUMERIC(5,4) "
        "USING CASE "
        "WHEN confidence = 'high' THEN 0.9000 "
        "WHEN confidence = 'medium' THEN 0.5000 "
        "WHEN confidence = 'low' THEN 0.2000 "
        "WHEN confidence IS NULL OR confidence = '' THEN NULL "
        "ELSE confidence::numeric END"
    )
