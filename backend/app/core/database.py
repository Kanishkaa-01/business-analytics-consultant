import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def create_active_engine():
    """
    Connect to PostgreSQL database for the development environment.
    Prevents silent fallback to SQLite when PostgreSQL is unavailable to ensure
    tests and development cannot accidentally execute against an unexpected database.
    Startup fails clearly with informative error logging.
    Passwords and credentials are never printed to terminal or logs.
    """
    db_url = settings.DATABASE_URL
    parsed = make_url(db_url)
    dialect_name = parsed.get_backend_name()
    db_name = parsed.database or "unknown"
    safe_target = parsed.render_as_string(hide_password=True)

    PERMITTED_DATABASE_NAME = "ba_consultant"
    if db_name != PERMITTED_DATABASE_NAME:
        raise RuntimeError(
            f"DATABASE ISOLATION VIOLATION: Database '{db_name}' is not permitted. "
            f"This development copy is strictly restricted to PostgreSQL database '{PERMITTED_DATABASE_NAME}'. "
            f"Connection attempt to '{db_name}' has been aborted."
        )

    def sanitize(msg: str) -> str:

        if parsed.password and parsed.password in msg:
            return msg.replace(parsed.password, "******")
        return msg

    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(
            f"Database connected successfully. Dialect: '{dialect_name}', Database: '{db_name}', Target: '{safe_target}'"
        )
        return engine, dialect_name, db_name
    except Exception as exc:
        clean_err = sanitize(str(exc))
        logger.error(
            f"Failed to connect to primary database '{db_name}' using dialect '{dialect_name}' ({safe_target}): {clean_err}"
        )
        if not getattr(settings, "ALLOW_SQLITE_FALLBACK", False):
            raise RuntimeError(
                f"Startup failed: PostgreSQL database '{db_name}' is unavailable ({clean_err}). "
                f"SQLite fallback is disabled for this development copy to ensure safe testing against '{db_name}' only."
            ) from None

        logger.warning(
            f"Falling back to local SQLite ({settings.SQLITE_FALLBACK_URL}) because ALLOW_SQLITE_FALLBACK is enabled."
        )
        sqlite_engine = create_engine(
            settings.SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False},
        )
        return sqlite_engine, "sqlite", "consultant.db"

engine, DB_DIALECT, DB_NAME = create_active_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.models import db_models  # noqa
    Base.metadata.create_all(bind=engine)
    # Safe schema patch for existing SQLite/Postgres tables
    try:
        with engine.connect() as conn:
            # Check existing columns in analysis_runs
            if DB_DIALECT == "sqlite":
                result = conn.execute(text("PRAGMA table_info(analysis_runs)"))
                existing_cols = {row[1] for row in result.fetchall()}
                new_cols = {
                    "analysis_name": "TEXT",
                    "dataset_version": "VARCHAR(64)",
                    "completed_at": "TIMESTAMP",
                    "error_message": "TEXT",
                    "forecast_data": "JSON",
                }
                for col_name, col_type in new_cols.items():
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE analysis_runs ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            elif DB_DIALECT == "postgresql":
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'analysis_runs'
                """))
                existing_cols = {row[0] for row in result.fetchall()}
                new_cols = {
                    "analysis_name": "VARCHAR(255)",
                    "dataset_version": "VARCHAR(64)",
                    "completed_at": "TIMESTAMP WITH TIME ZONE",
                    "error_message": "TEXT",
                    "forecast_data": "JSONB",
                }
                for col_name, col_type in new_cols.items():
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE analysis_runs ADD COLUMN {col_name} {col_type}"))
                conn.commit()
    except Exception as exc:
        logger.warning(f"Database schema patch notice: {exc}")

# Note: Database tables and schema patches are initialized explicitly via lifespan in main.py
# or by invoking init_db() during deployment/setup, avoiding unintended DDL on import.
