from collections.abc import AsyncIterator

from config.ttr_settings import get_ttr_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ttr_settings = get_ttr_settings()
ttr_engine = create_async_engine(ttr_settings.ttr_database_url, echo=False)
TTRSessionFactory = async_sessionmaker(ttr_engine, expire_on_commit=False)


async def get_ttr_session() -> AsyncIterator[AsyncSession]:
    async with TTRSessionFactory() as session:
        yield session
