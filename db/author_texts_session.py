from collections.abc import AsyncIterator

from config.author_texts_settings import get_author_texts_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

author_texts_settings = get_author_texts_settings()
author_texts_engine = create_async_engine(author_texts_settings.author_texts_database_url, echo=False)
AuthorTextsSessionFactory = async_sessionmaker(author_texts_engine, expire_on_commit=False)


async def get_author_texts_session() -> AsyncIterator[AsyncSession]:
    async with AuthorTextsSessionFactory() as session:
        yield session
