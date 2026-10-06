"""Only ORM queries; each feed query selects at most one text."""

from models.author_texts_models import AuthorText, AuthorTextStatus, AuthorTextsUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class AuthorTextsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def published_query(self):
        return (
            select(AuthorText)
            .where(AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED)
            .options(selectinload(AuthorText.likes))
            .execution_options(populate_existing=True)
        )

    async def list_published(self, min_text_length: int | None):
        query = self.published_query().order_by(AuthorText.author_text_id)
        if min_text_length is not None:
            query = query.where(AuthorText.text_length >= min_text_length)
        return (await self.session.scalars(query)).all()

    async def published(self, author_text_id: int, lock: bool = False):
        query = self.published_query().where(
            AuthorText.author_text_id == author_text_id
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def first_published(self, after_id: int | None = None):
        query = self.published_query().order_by(AuthorText.author_text_id).limit(1)
        if after_id is not None:
            query = query.where(AuthorText.author_text_id > after_id)
        return await self.session.scalar(query)

    async def draft(self, user_id: int, lock: bool = False):
        query = (
            select(AuthorText)
            .where(
                AuthorText.creator_id == user_id,
                AuthorText.author_texts_status == AuthorTextStatus.DRAFT,
            )
            .options(selectinload(AuthorText.likes))
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def user(self, user_id: int, lock: bool = False):
        query = select(AuthorTextsUser).where(
            AuthorTextsUser.author_texts_user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)
