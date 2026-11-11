"""Backfill subject timestamps required by the API response schema."""
from alembic import op
import sqlalchemy as sa

revision = "0002_subject_updated_at"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "subjects" in inspector.get_table_names():
        bind.execute(sa.text(
            "UPDATE subjects SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) "
            "WHERE updated_at IS NULL"
        ))


def downgrade():
    pass
