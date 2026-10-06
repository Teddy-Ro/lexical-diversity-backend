from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

AUTHOR_TEXTS_PROJECT_DIR = Path(__file__).resolve().parents[1]


class AuthorTextsSettings(BaseSettings):
    author_texts_database_url: str = (
        "postgresql+asyncpg://author_texts_user:ttr_password@127.0.0.1:55432/author_texts_database"
    )
    author_texts_frontend_root: Path = AUTHOR_TEXTS_PROJECT_DIR.parent / "lexical-diversity-frontend"
    author_texts_minio_public_url: str = "http://localhost:9000/author-texts-media"
    author_texts_current_user_id: int = 1
    author_texts_minio_endpoint: str = "127.0.0.1:9000"
    author_texts_minio_access_key: str = "minioadmin"
    author_texts_minio_secret_key: str = "minioadmin"
    author_texts_minio_secure: bool = False
    author_texts_minio_bucket: str = "author-texts-media"

    model_config = SettingsConfigDict(
        env_file=AUTHOR_TEXTS_PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_author_texts_settings() -> AuthorTextsSettings:
    return AuthorTextsSettings()
