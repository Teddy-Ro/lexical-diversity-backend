"""Read-only schema snapshot for checking the StarUML diagram."""

import asyncio
import json

from sqlalchemy import text

from db.author_texts_session import AuthorTextsSessionFactory


async def inspect_author_texts_schema():
    async with AuthorTextsSessionFactory() as session:
        result = await session.execute(text("""
            SELECT table_name, column_name, data_type,
                   character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name LIKE 'author_texts%'
            ORDER BY table_name, ordinal_position
        """))
        print(json.dumps([dict(row) for row in result.mappings()], ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(inspect_author_texts_schema())
