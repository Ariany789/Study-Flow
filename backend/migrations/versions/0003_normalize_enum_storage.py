"""Normalize legacy enum values before ORM reads them."""
from alembic import op
import sqlalchemy as sa


revision = "0003_normalize_enum_storage"
down_revision = "0002_subject_updated_at"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    for table in ("tasks", "goals"):
        if table in tables:
            bind.execute(sa.text(
                f"UPDATE {table} SET priority = lower(priority) "
                "WHERE upper(priority) IN ('LOW', 'MEDIUM', 'HIGH')"
            ))


def downgrade():
    pass
