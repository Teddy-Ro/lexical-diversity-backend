"""Generated object keys in PostgreSQL, file contents in MinIO."""

import logging
from functools import lru_cache
from uuid import uuid4

from config.author_texts_settings import get_author_texts_settings
from fastapi import HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error
from starlette.concurrency import run_in_threadpool
from urllib3 import PoolManager, Timeout
from urllib3.exceptions import HTTPError

AUTHOR_TEXTS_MEDIA_TYPES = {
    "image": {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"},
    "video": {"video/mp4": ".mp4", "video/webm": ".webm"},
}
AUTHOR_TEXTS_MEDIA_LIMITS = {"image": 10 * 1024 * 1024, "video": 50 * 1024 * 1024}


def author_texts_media_url(value: str | None) -> str | None:
    if value is None:
        return None
    # Preserve existing lab 2 seed URLs without a destructive data migration.
    if value.startswith(("http://", "https://", "/")):
        return value
    return f"{get_author_texts_settings().author_texts_minio_public_url.rstrip('/')}/{value}"


class AuthorTextsMedia:
    def __init__(self):
        settings = get_author_texts_settings()
        self.bucket = settings.author_texts_minio_bucket
        self.client = Minio(
            settings.author_texts_minio_endpoint,
            access_key=settings.author_texts_minio_access_key,
            secret_key=settings.author_texts_minio_secret_key,
            secure=settings.author_texts_minio_secure,
            http_client=PoolManager(timeout=Timeout(connect=3, read=30), retries=0),
        )

    async def validate(self, upload: UploadFile, kind: str) -> None:
        if upload.content_type not in AUTHOR_TEXTS_MEDIA_TYPES[kind]:
            raise HTTPException(422)
        if not upload.size or upload.size > AUTHOR_TEXTS_MEDIA_LIMITS[kind]:
            raise HTTPException(422)
        header = await upload.read(16)
        await upload.seek(0)
        signatures = {
            "image/jpeg": header.startswith(b"\xff\xd8\xff"),
            "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
            "video/mp4": header[4:8] == b"ftyp",
            "video/webm": header.startswith(b"\x1aE\xdf\xa3"),
        }
        if not signatures.get(upload.content_type):
            raise HTTPException(422)

    async def upload(self, upload: UploadFile, kind: str) -> str:
        key = f"author_texts_{uuid4().hex}{AUTHOR_TEXTS_MEDIA_TYPES[kind][upload.content_type]}"
        try:
            await run_in_threadpool(
                self.client.put_object,
                self.bucket,
                key,
                upload.file,
                length=upload.size,
                content_type=upload.content_type,
            )
        except (S3Error, HTTPError, OSError) as error:
            raise HTTPException(503) from error
        return key

    async def remove(self, key: str) -> None:
        try:
            await run_in_threadpool(self.client.remove_object, self.bucket, key)
        except (S3Error, HTTPError, OSError):
            logging.getLogger(__name__).exception("MinIO cleanup failed for %s", key)


@lru_cache(maxsize=1)
def get_author_texts_media() -> AuthorTextsMedia:
    return AuthorTextsMedia()
