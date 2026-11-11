"""create StudyFlow tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # The application can bootstrap SQLite for local development; this migration is the source of truth for deployments.
    bind = op.get_bind()
    if inspect(bind).has_table("users"): return
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("email", sa.String(255), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("theme", sa.String(20), nullable=False, server_default="system"), sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)); op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("subjects", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.Text()), sa.Column("color", sa.String(20), nullable=False), sa.Column("code", sa.String(30)), sa.Column("period", sa.String(30)), sa.Column("status", sa.String(20), nullable=False), sa.Column("start_date", sa.DateTime(timezone=True)), sa.Column("target_date", sa.DateTime(timezone=True)), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("goals", sa.Column("id", sa.String(36), primary_key=True), sa.Column("title", sa.String(180), nullable=False), sa.Column("description", sa.Text()), sa.Column("target", sa.Integer(), nullable=False), sa.Column("progress", sa.Integer(), nullable=False), sa.Column("priority", sa.String(20), nullable=False), sa.Column("subject_id", sa.String(36), sa.ForeignKey("subjects.id")), sa.Column("due_date", sa.DateTime(timezone=True)), sa.Column("status", sa.String(20), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("tasks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("title", sa.String(180), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(20), nullable=False), sa.Column("priority", sa.String(20), nullable=False), sa.Column("due_date", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("subject_id", sa.String(36), sa.ForeignKey("subjects.id")), sa.Column("goal_id", sa.String(36), sa.ForeignKey("goals.id")), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("study_sessions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("subject_id", sa.String(36), sa.ForeignKey("subjects.id")), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ended_at", sa.DateTime(timezone=True)), sa.Column("duration_minutes", sa.Integer(), nullable=False), sa.Column("notes", sa.Text()), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("notifications", sa.Column("id", sa.String(36), primary_key=True), sa.Column("title", sa.String(180), nullable=False), sa.Column("message", sa.String(500), nullable=False), sa.Column("kind", sa.String(30), nullable=False), sa.Column("read_at", sa.DateTime(timezone=True)), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("audit_logs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event", sa.String(80), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("ip_address", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

def downgrade():
    for table in ("audit_logs", "notifications", "study_sessions", "goals", "subjects", "tasks", "users"): op.drop_table(table)
