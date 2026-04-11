"""
Database configuration
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./easygrade.db")

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


def init_db():
    """Initialize database tables"""
    import models  # Import models to register them
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_user_demographics()

