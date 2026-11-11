"""Add persistent timer state and goal metric support."""
from alembic import op
import sqlalchemy as sa


revision = "0004_study_session_timer"
down_revision = "0003_normalize_enum_storage"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "goals" in tables:
        columns = {column["name"] for column in inspector.get_columns("goals")}
        if "metric" not in columns:
            op.add_column("goals", sa.Column("metric", sa.String(20), nullable=False, server_default="TASKS"))
        bind.execute(sa.text("UPDATE goals SET metric = 'TASKS' WHERE metric IS NULL OR metric = ''"))
    if "study_sessions" in tables:
        columns = {column["name"] for column in inspector.get_columns("study_sessions")}
        additions = {
            "duration_seconds": sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
            "paused_duration_seconds": sa.Column("paused_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
            "status": sa.Column("status", sa.String(20), nullable=False, server_default="COMPLETED"),
            "active_started_at": sa.Column("active_started_at", sa.DateTime(timezone=True)),
            "paused_at": sa.Column("paused_at", sa.DateTime(timezone=True)),
            "updated_at": sa.Column("updated_at", sa.DateTime(timezone=True)),
        }
        for name, column in additions.items():
            if name not in columns:
                op.add_column("study_sessions", column)
        bind.execute(sa.text("UPDATE study_sessions SET duration_seconds = COALESCE(duration_seconds, duration_minutes * 60, 0)"))
        bind.execute(sa.text("UPDATE study_sessions SET status = 'COMPLETED' WHERE status IS NULL OR status = ''"))
        bind.execute(sa.text("UPDATE study_sessions SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL"))
        op.create_index("uq_study_sessions_one_active", "study_sessions", ["user_id"], unique=True, sqlite_where=sa.text("status IN ('RUNNING', 'PAUSED')"))


def downgrade():
    pass
