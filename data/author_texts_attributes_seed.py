"""Idempotent examples of extra text attributes; preserve existing values."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import AuthorText, AuthorTextStatus, AuthorTextsAttribute, AuthorTextsAttributeValue

AUTHOR_TEXTS_ATTRIBUTE_EXAMPLES = {
    "Война и мир": {"Язык": "Русский", "Жанр": "Роман-эпопея"},
    "Капитанская дочка": {"Язык": "Русский", "Жанр": "Исторический роман"},
    "Дама с собачкой": {"Язык": "Русский", "Жанр": "Рассказ"},
    "Преступление и наказание": {"Язык": "Русский", "Жанр": "Роман"},
}


async def seed_author_texts_attributes(session: AsyncSession) -> None:
    names = ("Язык", "Жанр", "Литературное направление")
    definitions = {
        item.attribute_name: item
        for item in await session.scalars(
            select(AuthorTextsAttribute).where(AuthorTextsAttribute.attribute_name.in_(names))
        )
    }
    for name in names:
        if name not in definitions:
            definition = AuthorTextsAttribute(attribute_name=name)
            session.add(definition)
            definitions[name] = definition
    await session.flush()
    texts = (await session.execute(
        select(AuthorText.author_text_id, AuthorText.work_title).where(
            AuthorText.work_title.in_(AUTHOR_TEXTS_ATTRIBUTE_EXAMPLES),
            AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED,
        )
    )).all()
    if not texts:
        return
    existing = set((await session.execute(
        select(AuthorTextsAttributeValue.author_text_id, AuthorTextsAttributeValue.author_texts_attribute_id)
        .where(AuthorTextsAttributeValue.author_text_id.in_([row.author_text_id for row in texts]))
    )).all())
    for row in texts:
        for name, value in AUTHOR_TEXTS_ATTRIBUTE_EXAMPLES[row.work_title].items():
            attribute_id = definitions[name].author_texts_attribute_id
            if (row.author_text_id, attribute_id) not in existing:
                session.add(AuthorTextsAttributeValue(
                    author_text_id=row.author_text_id,
                    author_texts_attribute_id=attribute_id,
                    attribute_value=value,
                ))
