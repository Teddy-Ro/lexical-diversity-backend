import asyncio
from datetime import UTC, datetime

from db.ttr_session import TTRSessionFactory
from models.ttr_models import TTRLike, TTRText, TTRTextStatus, TTRUser
from services.ttr_statistics import calculate_ttr_statistics
from sqlalchemy import select

TTR_SEED_TEXTS = [
    (
        "Война и мир",
        "Лев Толстой",
        "Роман-эпопея о русском обществе в эпоху наполеоновских войн.",
        1869,
        587287,
        18210,
        "ttr-tolstoy-war-and-peace",
    ),
    (
        "Капитанская дочка",
        "Александр Пушкин",
        "Исторический роман о событиях Пугачёвского восстания.",
        1836,
        38420,
        8907,
        "ttr-pushkin-captains-daughter",
    ),
    (
        "Дама с собачкой",
        "Антон Чехов",
        "Рассказ о случайной встрече в Ялте и нравственном выборе героев.",
        1899,
        8710,
        3451,
        "ttr-chekhov-lady-with-dog",
    ),
    (
        "Преступление и наказание",
        "Фёдор Достоевский",
        "Роман о преступлении, вине и нравственном возрождении.",
        1866,
        211591,
        16984,
        "ttr-dostoevsky-crime-punishment",
    ),
]


async def seed_ttr_database() -> None:
    async with TTRSessionFactory() as session:
        if await session.scalar(select(TTRUser.ttr_user_id).limit(1)):
            print("TTR seed skipped: database already contains users.")
            return
        users = [TTRUser(username=f"researcher_{number}") for number in range(1, 13)]
        session.add_all(users)
        await session.flush()
        texts = []
        for (
            title,
            author,
            description,
            year,
            length,
            unique,
            media_name,
        ) in TTR_SEED_TEXTS:
            texts.append(
                TTRText(
                    work_title=title,
                    author_name=author,
                    short_description=description,
                    publication_year=year,
                    text_content="Демонстрационный текст из начального набора данных.",
                    ttr_status=TTRTextStatus.PUBLISHED,
                    ttr_image_url=f"http://localhost:9000/ttr-media/{media_name}.jpg",
                    ttr_video_url=f"http://localhost:9000/ttr-media/{media_name}.webm",
                    text_length=length,
                    unique_token_count=unique,
                    created_at=datetime.now(UTC),
                    published_at=datetime.now(UTC),
                    creator_id=users[1].ttr_user_id,
                )
            )
        draft_content = "Отцы и дети — текст черновика для TTR-анализа."
        draft_statistics = calculate_ttr_statistics(draft_content)
        texts.extend(
            [
                TTRText(
                    work_title="Отцы и дети",
                    author_name="Иван Тургенев",
                    short_description="",
                    publication_year=1862,
                    text_content=draft_content,
                    ttr_status=TTRTextStatus.DRAFT,
                    text_length=draft_statistics.text_length,
                    unique_token_count=draft_statistics.unique_token_count,
                    creator_id=users[0].ttr_user_id,
                ),
                TTRText(
                    work_title="Демон",
                    author_name="Михаил Лермонтов",
                    short_description="Поэма о мятежном духе, любви и одиночестве.",
                    publication_year=1842,
                    text_content="Демон — удалённый демонстрационный текст.",
                    ttr_status=TTRTextStatus.DELETED,
                    text_length=17900,
                    unique_token_count=5430,
                    creator_id=users[1].ttr_user_id,
                ),
            ]
        )
        session.add_all(texts)
        await session.flush()
        session.add_all(
            TTRLike(researcher_id=user.ttr_user_id, ttr_text_id=texts[0].ttr_text_id)
            for user in users[:8]
        )
        await session.commit()
        print("TTR seed completed.")


if __name__ == "__main__":
    asyncio.run(seed_ttr_database())
