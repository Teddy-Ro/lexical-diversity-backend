"""Optional actor for public reads, required actor for private operations."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyCookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.author_texts_settings import get_author_texts_settings
from db.author_texts_session import get_author_texts_session
from models.author_texts_models import AuthorTextsUser
from services.author_texts_sessions import AuthorTextsSessions, get_author_texts_sessions


@dataclass(frozen=True)
class AuthorTextsCurrentUser:
    author_texts_user_id: int


author_texts_cookie = APIKeyCookie(
    name=get_author_texts_settings().author_texts_session_cookie,
    scheme_name="AuthorTextsSession", auto_error=False,
    description="Выполните POST /author_texts_users/login в Swagger: браузер сохранит HttpOnly cookie автоматически.",
)
AuthorTextsSessionCookie = Annotated[str | None, Security(author_texts_cookie)]


async def get_current_author_texts_user(
    session_id: AuthorTextsSessionCookie,
    sessions: Annotated[AuthorTextsSessions, Depends(get_author_texts_sessions)],
    db: Annotated[AsyncSession, Depends(get_author_texts_session)],
) -> AuthorTextsCurrentUser | None:
    user_id = await sessions.user_id(session_id)
    if user_id is None:
        return None
    exists = await db.scalar(select(AuthorTextsUser.author_texts_user_id).where(
        AuthorTextsUser.author_texts_user_id == user_id
    ))
    return AuthorTextsCurrentUser(exists) if exists is not None else None


async def require_author_texts_user(
    actor: Annotated[AuthorTextsCurrentUser | None, Depends(get_current_author_texts_user)],
) -> AuthorTextsCurrentUser:
    if actor is None:
        raise HTTPException(401)
    return actor
