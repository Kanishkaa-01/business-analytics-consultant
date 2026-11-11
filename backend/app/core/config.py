import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PERMITTED_DATABASE_NAME = "ba_consultant"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Business Analytics Consultant — Explainable Business Decision Support System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    PORT: int = 8001
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ba_consultant"
    SQLITE_FALLBACK_URL: str = "sqlite:///./consultant.db"
    ALLOW_SQLITE_FALLBACK: bool = False

    # File storage
    UPLOAD_DIR: Path = Path("./data_storage/uploads")
    MAX_UPLOAD_SIZE_MB: int = 50

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=(_BACKEND_DIR / ".env", ".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_isolation(cls, v: str) -> str:
        try:
            parsed = make_url(v)
            db_name = parsed.database
        except Exception as err:
            raise ValueError(f"Invalid DATABASE_URL format: {err}") from err

        if db_name != PERMITTED_DATABASE_NAME:
            raise ValueError(
                f"DATABASE ISOLATION VIOLATION: Database name '{db_name}' is not permitted. "
                f"This second project copy is strictly restricted to '{PERMITTED_DATABASE_NAME}'. "
                f"Connections to any other database (including 'consultant') are forbidden."
            )
        return v

    @field_validator("ALLOW_SQLITE_FALLBACK")
    @classmethod
    def validate_sqlite_fallback(cls, v: bool) -> bool:
        if v:
            raise ValueError(
                "DATABASE ISOLATION VIOLATION: ALLOW_SQLITE_FALLBACK must remain False in this copy "
                "to prevent accidental execution against an unintended SQLite database."
            )
        return v


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

