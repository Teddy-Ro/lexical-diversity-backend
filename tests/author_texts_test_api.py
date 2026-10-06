"""Run with AUTHOR_TEXTS_RUN_DB_TESTS=1; test rows are rolled back."""

import os
import unittest
from pathlib import Path
from uuid import uuid4

import httpx
from api.author_texts_api import author_texts_api
from api.author_texts_dependencies import (
    AuthorTextsCurrentUser,
    get_current_author_texts_user,
)
from author_texts_main import app
from config.author_texts_settings import get_author_texts_settings
from db.author_texts_base import AuthorTextsBase
from db.author_texts_session import get_author_texts_session
from models.author_texts_models import (
    AuthorText,
    AuthorTextsLike,
    AuthorTextStatus,
    AuthorTextsUser,
)
from services.author_texts_media import AuthorTextsMedia, get_author_texts_media
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


class AuthorTextsMemoryMedia(AuthorTextsMedia):
    def __init__(self):
        self.objects = {}
        self.fail_video = False

    async def upload(self, upload, kind):
        if kind == "video" and self.fail_video:
            from fastapi import HTTPException

            raise HTTPException(503)
        key = f"author_texts_{uuid4().hex}.{'jpg' if kind == 'image' else 'webm'}"
        self.objects[key] = await upload.read()
        return key

    async def remove(self, key):
        self.objects.pop(key, None)


class AuthorTextsApiContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_singleton(self):
        first = get_current_author_texts_user()
        self.assertIs(first, get_current_author_texts_user())
        self.assertEqual(first.author_texts_user_id, 1)

    async def test_empty_errors_and_stubs(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for path in ("/api/missing", "/api/author_texts/not-an-id"):
                response = await client.get(path)
                self.assertIn(response.status_code, (404, 422))
                self.assertEqual(response.content, b"")
            for path in ("login", "logout"):
                response = await client.post(f"/api/author_texts_users/{path}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"")
                self.assertNotIn("set-cookie", response.headers)
            response = await client.get("/api/openapi.json")
            self.assertEqual(response.status_code, 200)
            schema = response.json()
            fields = schema["components"]["schemas"]["AuthorTextsResponse"][
                "properties"
            ]
            self.assertNotIn("author_texts_status", fields)
            self.assertNotIn("status", fields)
            self.assertNotIn("password_hash", fields)
            self.assertEqual(
                set(fields),
                set(schema["components"]["schemas"]["AuthorTextsResponse"]["required"]),
            )


@unittest.skipUnless(
    os.getenv("AUTHOR_TEXTS_RUN_DB_TESTS") == "1"
    or os.getenv("AUTHOR_TEXTS_TEST_SQLITE") == "1",
    "Database integration test",
)
class AuthorTextsApiFlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = get_author_texts_settings()
        self.sqlite = os.getenv("AUTHOR_TEXTS_TEST_SQLITE") == "1"
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:"
            if self.sqlite
            else self.settings.author_texts_database_url
        )
        self.connection = await self.engine.connect()
        if self.sqlite:
            # PostgreSQL partial index syntax has an equivalent for isolated SQLite tests.
            for index in AuthorText.__table__.indexes:
                if index.name == "uq_author_texts_one_draft_per_user":
                    index.dialect_options["sqlite"]["where"] = index.dialect_options[
                        "postgresql"
                    ]["where"]
            await self.connection.run_sync(AuthorTextsBase.metadata.create_all)
            await self.connection.commit()
        self.transaction = await self.connection.begin()
        self.session = AsyncSession(
            bind=self.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        self.user = AuthorTextsUser(
            username=f"api_{uuid4().hex}", password_hash="test-only"
        )
        self.other = AuthorTextsUser(
            username=f"api_{uuid4().hex}", password_hash="test-only"
        )
        self.session.add_all([self.user, self.other])
        await self.session.flush()
        self.actor_id = self.user.author_texts_user_id
        self.media = AuthorTextsMemoryMedia()

        async def session_override():
            yield self.session

        author_texts_api.dependency_overrides[get_author_texts_session] = (
            session_override
        )
        author_texts_api.dependency_overrides[get_current_author_texts_user] = lambda: (
            AuthorTextsCurrentUser(self.actor_id)
        )
        author_texts_api.dependency_overrides[get_author_texts_media] = lambda: (
            self.media
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        self.payload = {
            "work_title": "Тестовый текст",
            "author_name": "Автор",
            "publication_year": None,
            "short_description": "Проверка API",
            "text_content": "Мир, мир! Война и мир.",
        }

    async def asyncTearDown(self):
        await self.client.aclose()
        author_texts_api.dependency_overrides.clear()
        await self.session.close()
        await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    def files(self):
        return {
            "author_texts_image": (
                "фото.jpg",
                b"\xff\xd8\xff" + b"x" * 20,
                "image/jpeg",
            ),
            "author_texts_video": (
                "видео.webm",
                b"\x1aE\xdf\xa3" + b"x" * 20,
                "video/webm",
            ),
        }

    async def create(self):
        response = await self.client.post(
            "/api/author_texts",
            data={"work_title": "Тестовый текст"},
            files=self.files(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_full_flow(self):
        self.assertEqual(
            (await self.client.get("/api/author_texts/draft")).status_code, 404
        )
        draft = await self.create()
        text_id = draft["author_text_id"]
        self.assertIsNone(draft["text_length"])
        self.assertIsNone(draft["text_content"])
        self.assertEqual(draft["author_texts_like_count"], 0)
        self.assertNotIn("author_texts_status", draft)
        row = await self.session.get(AuthorText, text_id)
        self.assertNotIn("http", row.author_texts_image_url)
        self.assertTrue(row.author_texts_image_url.isascii())
        self.assertEqual(row.creator_id, self.actor_id)
        response = await self.client.post(
            "/api/author_texts", data={"work_title": "Повтор"}, files=self.files()
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.media.objects), 2)
        self.assertEqual(
            (await self.client.get(f"/api/author_texts/{text_id}")).status_code, 404
        )
        self.assertEqual(
            (await self.client.get("/api/author_texts/draft")).json(), draft
        )

        response = await self.client.put(
            f"/api/author_texts/{text_id}/publish", json=self.payload
        )
        self.assertEqual(response.status_code, 200)
        published = response.json()
        self.assertEqual(set(draft), set(published))
        self.assertEqual(
            (
                published["text_length"],
                published["unique_token_count"],
                published["author_texts_ratio"],
            ),
            (5, 3, 0.6),
        )
        self.assertIsNone(published["publication_year"])
        self.assertEqual(
            (
                await self.client.put(
                    f"/api/author_texts/{text_id}/publish", json=self.payload
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.get("/api/author_texts/draft")).status_code, 404
        )
        self.assertEqual(
            (await self.client.get("/api/author_texts/feed")).status_code, 200
        )
        self.assertEqual(
            (
                await self.client.get(f"/api/author_texts/{text_id}?next=true")
            ).status_code,
            200,
        )
        filtered = (await self.client.get("/api/author_texts?min_text_length=6")).json()
        self.assertNotIn(text_id, [item["author_text_id"] for item in filtered])
        for value, count in ((1, 1), (1, 1), (0, 0), (0, 0), (1, 1)):
            response = await self.client.post(
                f"/api/author_texts/{text_id}/like", json={"value": value}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["author_texts_like_count"], count)
            actual = await self.session.scalar(
                select(func.count())
                .select_from(AuthorTextsLike)
                .where(AuthorTextsLike.author_text_id == text_id)
            )
            self.assertEqual(actual, count)
        response = await self.client.delete(f"/api/author_texts/{text_id}")
        self.assertEqual((response.status_code, response.content), (200, b""))
        await self.session.refresh(row)
        self.assertEqual(row.author_texts_status, AuthorTextStatus.DELETED)
        for method, path in (
            ("get", f"/api/author_texts/{text_id}"),
            ("delete", f"/api/author_texts/{text_id}"),
        ):
            response = await getattr(self.client, method)(path)
            self.assertEqual((response.status_code, response.content), (404, b""))
        self.assertEqual(
            (
                await self.client.post(
                    f"/api/author_texts/{text_id}/like", json={"value": 1}
                )
            ).status_code,
            404,
        )
        self.assertNotIn(
            text_id,
            [
                item["author_text_id"]
                for item in (await self.client.get("/api/author_texts")).json()
            ],
        )

    async def test_ownership_and_validation(self):
        draft = await self.create()
        text_id = draft["author_text_id"]
        for field in (
            "author_text_id",
            "creator_id",
            "author_texts_status",
            "text_length",
            "unique_token_count",
        ):
            response = await self.client.put(
                f"/api/author_texts/{text_id}/publish", json={**self.payload, field: 1}
            )
            self.assertEqual((response.status_code, response.content), (422, b""))

        self.actor_id = self.other.author_texts_user_id
        self.assertEqual(
            (await self.client.get("/api/author_texts/draft")).status_code, 404
        )
        self.assertEqual(
            (
                await self.client.put(
                    f"/api/author_texts/{text_id}/publish", json=self.payload
                )
            ).status_code,
            404,
        )
        self.actor_id = self.user.author_texts_user_id
        await self.client.put(f"/api/author_texts/{text_id}/publish", json=self.payload)
        self.actor_id = self.other.author_texts_user_id
        self.assertEqual(
            (await self.client.delete(f"/api/author_texts/{text_id}")).status_code, 404
        )
        response = await self.client.post(
            f"/api/author_texts/{text_id}/like", json={"value": 1}
        )
        self.assertEqual(response.json()["author_texts_like_count"], 1)
        for value in (2, -1, "1", True):
            response = await self.client.post(
                f"/api/author_texts/{text_id}/like", json={"value": value}
            )
            self.assertEqual((response.status_code, response.content), (422, b""))

    async def test_feed_order_and_wrap(self):
        first = await self.create()
        await self.client.put(
            f"/api/author_texts/{first['author_text_id']}/publish", json=self.payload
        )
        second = await self.create()
        await self.client.put(
            f"/api/author_texts/{second['author_text_id']}/publish", json=self.payload
        )
        response = await self.client.get(
            f"/api/author_texts/{first['author_text_id']}?next=true"
        )
        self.assertEqual(response.json()["author_text_id"], second["author_text_id"])
        first_published = await self.session.scalar(
            select(func.min(AuthorText.author_text_id)).where(
                AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED
            )
        )
        response = await self.client.get(
            f"/api/author_texts/{second['author_text_id']}?next=true"
        )
        self.assertEqual(response.json()["author_text_id"], first_published)
        self.assertEqual(
            (await self.client.get("/api/author_texts/feed")).json()["author_text_id"],
            first_published,
        )

    async def test_upload_validation_and_compensation(self):
        files = self.files()
        files["author_texts_image"] = ("fake.jpg", b"not an image", "image/jpeg")
        response = await self.client.post(
            "/api/author_texts", data={"work_title": "Test"}, files=files
        )
        self.assertEqual(response.status_code, 422)
        response = await self.client.post(
            "/api/author_texts",
            data={"work_title": "Test", "creator_id": "1"},
            files=self.files(),
        )
        self.assertEqual(response.status_code, 422)
        self.media.fail_video = True
        response = await self.client.post(
            "/api/author_texts", data={"work_title": "Test"}, files=self.files()
        )
        self.assertEqual((response.status_code, response.content), (503, b""))
        self.assertEqual(self.media.objects, {})
        self.assertEqual(
            (await self.client.get("/api/author_texts/draft")).status_code, 404
        )

    async def test_registration(self):
        payload = {"username": f"registered_{uuid4().hex}", "password": "test-password"}
        response = await self.client.post(
            "/api/author_texts_users/register", json=payload
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()), {"author_texts_user_id", "username"})
        row = await self.session.get(
            AuthorTextsUser, response.json()["author_texts_user_id"]
        )
        self.assertTrue(row.password_hash.startswith("pbkdf2_sha256$"))
        self.assertNotEqual(row.password_hash, payload["password"])
        response = await self.client.post(
            "/api/author_texts_users/register", json=payload
        )
        self.assertEqual((response.status_code, response.content), (409, b""))

    @unittest.skipUnless(
        os.getenv("AUTHOR_TEXTS_RUN_MINIO_TESTS") == "1", "Real MinIO upload"
    )
    async def test_real_minio(self):
        media = AuthorTextsMedia()
        author_texts_api.dependency_overrides[get_author_texts_media] = lambda: media
        public = Path(self.settings.author_texts_frontend_root) / "public" / "media"
        files = {
            "author_texts_image": (
                "фото.jpg",
                (public / "author_texts_default.jpg").read_bytes(),
                "image/jpeg",
            ),
            "author_texts_video": (
                "видео.webm",
                (public / "author_texts_default.webm").read_bytes(),
                "video/webm",
            ),
        }
        response = await self.client.post(
            "/api/author_texts", data={"work_title": "MinIO test"}, files=files
        )
        self.assertEqual(response.status_code, 201)
        uploaded = response.json()
        keys = [
            uploaded[name].rsplit("/", 1)[1]
            for name in ("author_texts_image_url", "author_texts_video_url")
        ]
        try:
            async with httpx.AsyncClient() as client:
                for field, source in (
                    ("author_texts_image_url", "author_texts_image"),
                    ("author_texts_video_url", "author_texts_video"),
                ):
                    result = await client.get(uploaded[field])
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual(result.content, files[source][1])
        finally:
            for key in keys:
                await media.remove(key)


if __name__ == "__main__":
    unittest.main()
