from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_compatible_schema():
    """Applies additive local upgrades without deleting existing user data."""
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "weekly_study_goal_minutes" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN weekly_study_goal_minutes INTEGER NOT NULL DEFAULT 300"
                ))
    if "tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    with engine.begin() as connection:
        if "subject_id" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN subject_id VARCHAR(36)"))
        if "goal_id" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN goal_id VARCHAR(36)"))
        # Versões antigas gravaram prioridades com o valor da API (MEDIUM),
        # enquanto o SQLAlchemy Enum usa o nome persistido (medium).
        connection.execute(text(
            "UPDATE tasks SET priority = lower(priority) "
            "WHERE upper(priority) IN ('LOW', 'MEDIUM', 'HIGH')"
        ))
    inspector = inspect(engine)
    if "goals" in inspector.get_table_names():
        goal_columns = {column["name"] for column in inspector.get_columns("goals")}
        with engine.begin() as connection:
            if "priority" not in goal_columns:
                connection.execute(text("ALTER TABLE goals ADD COLUMN priority VARCHAR(20) DEFAULT 'MEDIUM'"))
            if "metric" not in goal_columns:
                connection.execute(text("ALTER TABLE goals ADD COLUMN metric VARCHAR(20) DEFAULT 'TASKS'"))
            if "subject_id" not in goal_columns:
                connection.execute(text("ALTER TABLE goals ADD COLUMN subject_id VARCHAR(36)"))
            connection.execute(text(
                "UPDATE goals SET priority = lower(priority) "
                "WHERE upper(priority) IN ('LOW', 'MEDIUM', 'HIGH')"
            ))
            connection.execute(text("UPDATE goals SET metric = 'TASKS' WHERE metric IS NULL OR metric = ''"))
    inspector = inspect(engine)
    if "study_sessions" in inspector.get_table_names():
        session_columns = {column["name"] for column in inspector.get_columns("study_sessions")}
        with engine.begin() as connection:
            if "duration_seconds" not in session_columns:
                connection.execute(text("ALTER TABLE study_sessions ADD COLUMN duration_seconds INTEGER DEFAULT 0"))
            if "paused_duration_seconds" not in session_columns:
                connection.execute(text("ALTER TABLE study_sessions ADD COLUMN paused_duration_seconds INTEGER DEFAULT 0"))
            if "status" not in session_columns:
                connection.execute(text("ALTER TABLE study_sessions ADD COLUMN status VARCHAR(20) DEFAULT 'COMPLETED'"))
            if "active_started_at" not in session_columns:
                connection.execute(text("ALTER TABLE study_sessions ADD COLUMN active_started_at DATETIME"))
            if "paused_at" not in session_columns:
                connection.execute(text("ALTER TABLE study_sessions ADD COLUMN paused_at DATETIME"))
            if "updated_at" not in session_columns:
                connection.execute(text("ALTER TABLE study_sessions ADD COLUMN updated_at DATETIME"))
            connection.execute(text("UPDATE study_sessions SET duration_seconds = COALESCE(duration_seconds, duration_minutes * 60, 0) WHERE duration_seconds IS NULL OR duration_seconds = 0"))
            connection.execute(text("UPDATE study_sessions SET status = 'COMPLETED' WHERE status IS NULL OR status = ''"))
            connection.execute(text("UPDATE study_sessions SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_study_sessions_one_active ON study_sessions(user_id) WHERE status IN ('RUNNING', 'PAUSED')"))
    if "subjects" in inspector.get_table_names():
        subject_columns = {column["name"] for column in inspector.get_columns("subjects")}
        with engine.begin() as connection:
            if "status" not in subject_columns:
                connection.execute(text("ALTER TABLE subjects ADD COLUMN status VARCHAR(20) DEFAULT 'PLANNED'"))
            if "start_date" not in subject_columns:
                connection.execute(text("ALTER TABLE subjects ADD COLUMN start_date DATETIME"))
            if "target_date" not in subject_columns:
                connection.execute(text("ALTER TABLE subjects ADD COLUMN target_date DATETIME"))
            if "updated_at" not in subject_columns:
                connection.execute(text("ALTER TABLE subjects ADD COLUMN updated_at DATETIME"))
            # Registros criados por versões antigas podem ter a coluna nula,
            # mas SubjectOutput exige uma data para serializar a resposta.
            connection.execute(text(
                "UPDATE subjects SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) "
                "WHERE updated_at IS NULL"
            ))
