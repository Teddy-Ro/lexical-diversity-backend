"""Opaque session cookies; Redis is the authoritative session store."""

import re
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from config.author_texts_settings import get_author_texts_settings

AUTHOR_TEXTS_SESSION_PREFIX = "author_texts:session:"


def valid_author_texts_session(session_id: str | None) -> bool:
    return bool(session_id and re.fullmatch(r"[A-Za-z0-9_-]{43}", session_id))


class AuthorTextsSessions:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def create(self, user_id: int) -> str:
        session_id = secrets.token_urlsafe(32)
        try:
            await self.redis.set(
                AUTHOR_TEXTS_SESSION_PREFIX + session_id, str(user_id),
                ex=get_author_texts_settings().author_texts_session_ttl,
            )
        except RedisError as error:
            raise HTTPException(503) from error
        return session_id

    async def user_id(self, session_id: str | None) -> int | None:
        if not valid_author_texts_session(session_id):
            return None
        try:
            value = await self.redis.get(AUTHOR_TEXTS_SESSION_PREFIX + session_id)
        except RedisError as error:
            raise HTTPException(503) from error
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    async def destroy(self, session_id: str | None) -> None:
        if valid_author_texts_session(session_id):
            try:
                await self.redis.delete(AUTHOR_TEXTS_SESSION_PREFIX + session_id)
            except RedisError as error:
                raise HTTPException(503) from error


def create_author_texts_redis() -> Redis:
    return Redis.from_url(
        get_author_texts_settings().author_texts_redis_url,
        decode_responses=True, socket_connect_timeout=3, socket_timeout=3,
    )


@asynccontextmanager
async def author_texts_api_lifespan(app):
    redis = create_author_texts_redis()
    app.state.author_texts_sessions = AuthorTextsSessions(redis)
    try:
        yield
    finally:
        await redis.aclose()
        del app.state.author_texts_sessions


async def get_author_texts_sessions(request: Request) -> AsyncIterator[AuthorTextsSessions]:
    shared = getattr(request.app.state, "author_texts_sessions", None)
    if shared is not None:
        yield shared
        return
    redis = create_author_texts_redis()
    try:
        yield AuthorTextsSessions(redis)
    finally:
        await redis.aclose()


def check_author_texts_origin(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme != request.url.scheme or parsed.netloc != request.url.netloc:
            raise HTTPException(403)
    elif request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403)
