import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def create_active_engine():
    """
    Attempt to connect to PostgreSQL. If connection fails or is not available,
    gracefully fall back to local SQLite to ensure uninterrupted development.
    """
    db_url = settings.DATABASE_URL
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected to primary database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        return engine, "postgresql"
    except Exception as exc:
        logger.warning(
            f"Primary database connection ({db_url}) failed: {exc}. "
            f"Falling back to local SQLite ({settings.SQLITE_FALLBACK_URL})."
        )
        sqlite_engine = create_engine(
            settings.SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False},
        )
        return sqlite_engine, "sqlite"

engine, DB_DIALECT = create_active_engine()
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

# Auto-initialize tables
init_db()
