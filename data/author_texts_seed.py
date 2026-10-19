import asyncio

from db.author_texts_session import AuthorTextsSessionFactory
from models.author_texts_models import AuthorTextsLike, AuthorText, AuthorTextStatus, AuthorTextsUser
from services.author_texts_passwords import hash_author_texts_password
from sqlalchemy import select

AUTHOR_TEXTS_SEED_TEXTS = [
    (
        "Война и мир",
        "Роман-эпопея о русском обществе в эпоху наполеоновских войн.",
        587287,
        18210,
        "author_texts-tolstoy-war-and-peace",
    ),
    (
        "Капитанская дочка",
        "Исторический роман о событиях Пугачёвского восстания.",
        38420,
        8907,
        "author_texts-pushkin-captains-daughter",
    ),
    (
        "Дама с собачкой",
        "Рассказ о случайной встрече в Ялте и нравственном выборе героев.",
        8710,
        3451,
        "author_texts-chekhov-lady-with-dog",
    ),
    (
        "Преступление и наказание",
        "Роман о преступлении, вине и нравственном возрождении.",
        211591,
        16984,
        "author_texts-dostoevsky-crime-punishment",
    ),
]


async def seed_author_texts_database() -> None:
    async with AuthorTextsSessionFactory() as session:
        if await session.scalar(select(AuthorTextsUser.author_texts_user_id).limit(1)):
            print("TTR seed skipped: database already contains users.")
            return
        users = [
            AuthorTextsUser(
                username=f"researcher_{number}",
                password_hash=hash_author_texts_password("author_texts_demo"),
            )
            for number in range(1, 13)
        ]
        session.add_all(users)
        await session.flush()
        texts = []
        for (
            title,
            description,
            length,
            unique,
            media_name,
        ) in AUTHOR_TEXTS_SEED_TEXTS:
            texts.append(
                AuthorText(
                    work_title=title,
                    short_description=description,
                    author_texts_status=AuthorTextStatus.PUBLISHED,
                    author_texts_image_url=f"http://localhost:9000/author-texts-media/{media_name}.jpg",
                    author_texts_video_url=f"http://localhost:9000/author-texts-media/{media_name}.webm",
                    text_length=length,
                    unique_token_count=unique,
                    creator_id=users[1].author_texts_user_id,
                )
            )
        texts.extend(
            [
                AuthorText(
                    work_title="Отцы и дети",
                    author_texts_image_url="/author_texts-assets/media/author_texts_default.jpg",
                    author_texts_video_url="/author_texts-assets/media/author_texts_default.webm",
                    short_description="",
                    author_texts_status=AuthorTextStatus.DRAFT,
                    text_length=None,
                    unique_token_count=None,
                    creator_id=users[0].author_texts_user_id,
                ),
                AuthorText(
                    work_title="Демон",
                    author_texts_image_url="/author_texts-assets/media/author_texts_default.jpg",
                    author_texts_video_url="/author_texts-assets/media/author_texts_default.webm",
                    short_description="Поэма о мятежном духе, любви и одиночестве.",
                    author_texts_status=AuthorTextStatus.DELETED,
                    text_length=17900,
                    unique_token_count=5430,
                    creator_id=users[1].author_texts_user_id,
                ),
            ]
        )
        session.add_all(texts)
        await session.flush()
        session.add_all(
            AuthorTextsLike(researcher_id=user.author_texts_user_id, author_text_id=texts[0].author_text_id)
            for user in users[:8]
        )
        await session.commit()
        print("TTR seed completed.")


if __name__ == "__main__":
    asyncio.run(seed_author_texts_database())
