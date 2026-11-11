"""Add each user's weekly study target."""
from alembic import op
import sqlalchemy as sa


revision = "0005_weekly_study_goal"
down_revision = "0004_study_session_timer"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "weekly_study_goal_minutes" not in columns:
            op.add_column("users", sa.Column(
                "weekly_study_goal_minutes", sa.Integer(), nullable=False, server_default="300"
            ))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names() and "weekly_study_goal_minutes" in {
        column["name"] for column in inspector.get_columns("users")
    }:
        op.drop_column("users", "weekly_study_goal_minutes")
