from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

TTR_PROJECT_DIR = Path(__file__).resolve().parents[1]


class TTRSettings(BaseSettings):
    ttr_database_url: str = (
        "postgresql+asyncpg://ttr_user:ttr_password@127.0.0.1:55432/ttr_database"
    )
    ttr_frontend_root: Path = TTR_PROJECT_DIR.parent / "lexical-diversity-frontend"
    ttr_minio_public_url: str = "http://localhost:9000/ttr-media"
    ttr_current_user_id: int = 1

    model_config = SettingsConfigDict(
        env_file=TTR_PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_ttr_settings() -> TTRSettings:
    return TTRSettings()
