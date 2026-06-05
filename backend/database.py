"""
Database configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


def _resolve_database_url() -> str:
    """Normalize DATABASE_URL for local dev, Render Postgres, and empty env placeholders."""
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        return "sqlite:///./easygrade.db"
    # Render/Heroku provide postgres://; SQLAlchemy 2.x expects postgresql://
    if raw.startswith("postgres://"):
        return "postgresql://" + raw[len("postgres://") :]
    return raw


DATABASE_URL = _resolve_database_url()

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_sqlite_user_demographics():
    """Add user profile columns when upgrading an existing SQLite database."""
    if "sqlite" not in DATABASE_URL:
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    existing = {c["name"] for c in insp.get_columns("users")}
    alters: list[str] = []
    if "institution" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN institution VARCHAR(255)")
    if "country" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN country VARCHAR(128)")
    if "major_department" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN major_department VARCHAR(255)")
    if "year_of_study" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN year_of_study INTEGER")
    if "gender" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN gender VARCHAR(64)")
    if "student_id" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN student_id VARCHAR(128)")
    if "date_of_birth" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN date_of_birth DATE")
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))


def migrate_questions_outline_title():
    """Add outline_title to questions when upgrading an existing database."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("questions"):
        return
    existing = {c["name"] for c in insp.get_columns("questions")}
    if "outline_title" in existing:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE questions ADD COLUMN outline_title VARCHAR(500)"))


def migrate_user_reminder_preferences():
    """Add reminder preference columns when upgrading an existing database."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    existing = {c["name"] for c in insp.get_columns("users")}
    dialect = engine.dialect.name
    alters: list[str] = []
    if "remind_exam_deadlines_enabled" not in existing:
        if dialect == "sqlite":
            alters.append(
                "ALTER TABLE users ADD COLUMN remind_exam_deadlines_enabled INTEGER NOT NULL DEFAULT 1"
            )
        else:
            alters.append(
                "ALTER TABLE users ADD COLUMN remind_exam_deadlines_enabled BOOLEAN NOT NULL DEFAULT TRUE"
            )
    if "remind_exam_offsets_hours" not in existing:
        alters.append("ALTER TABLE users ADD COLUMN remind_exam_offsets_hours VARCHAR(512)")
    if "remind_teaching_deadlines_enabled" not in existing:
        if dialect == "sqlite":
            alters.append(
                "ALTER TABLE users ADD COLUMN remind_teaching_deadlines_enabled INTEGER NOT NULL DEFAULT 1"
            )
        else:
            alters.append(
                "ALTER TABLE users ADD COLUMN remind_teaching_deadlines_enabled BOOLEAN NOT NULL DEFAULT TRUE"
            )
    if alters:
        with engine.begin() as conn:
            for stmt in alters:
                conn.execute(text(stmt))
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("users")}
    if "remind_exam_offsets_hours" in cols:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE users SET remind_exam_offsets_hours = '[168,72,24]' "
                    "WHERE remind_exam_offsets_hours IS NULL OR trim(remind_exam_offsets_hours) = ''"
                )
            )


def init_db():
    """Initialize database tables"""
    import models  # Import models to register them
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_user_demographics()
    migrate_questions_outline_title()
    migrate_user_reminder_preferences()

