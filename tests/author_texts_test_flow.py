"""Integration check against PostgreSQL; every test rolls back its own rows.

Set AUTHOR_TEXTS_RUN_DB_TESTS=1 after applying migrations to enable.
"""

import os
import unittest
import uuid
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from api.author_texts_handlers import author_texts_settings
from author_texts_main import app
from db.author_texts_session import get_author_texts_session
from models.author_texts_models import AuthorText, AuthorTextsLike, AuthorTextsUser, AuthorTextStatus
from services.author_texts_passwords import hash_author_texts_password


@unittest.skipUnless(os.getenv("AUTHOR_TEXTS_RUN_DB_TESTS") == "1", "PostgreSQL integration test")
class AuthorTextsFlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(author_texts_settings.author_texts_database_url)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.session = AsyncSession(bind=self.connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        user = AuthorTextsUser(username=f"flow_{uuid.uuid4().hex}", password_hash=hash_author_texts_password("test-only"))
        self.session.add(user)
        await self.session.flush()
        self.old_user = author_texts_settings.author_texts_current_user_id
        author_texts_settings.author_texts_current_user_id = user.author_texts_user_id

        async def session_override():
            yield self.session

        app.dependency_overrides[get_author_texts_session] = session_override
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        author_texts_settings.author_texts_current_user_id = self.old_user
        await self.session.close()
        await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    async def test_draft_publish_filter_likes_next_delete(self):
        page = await self.client.get("/author_texts/add")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.text.count('type="file"'), 2)
        self.assertIn('>Далее</button>', page.text)
        self.assertNotIn('name="text_content"', page.text)
        self.assertNotIn('<script', page.text)

        response = await self.client.post("/author_texts/drafts", data={"work_title": "   "})
        self.assertEqual(response.status_code, 422)
        response = await self.client.post("/author_texts/drafts", data={"work_title": "Тестовый текст"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/author_texts/add')
        draft = await self.session.scalar(select(AuthorText).where(AuthorText.creator_id == author_texts_settings.author_texts_current_user_id))
        text_id = draft.author_text_id
        self.assertEqual(draft.author_texts_status, AuthorTextStatus.DRAFT)
        self.assertIsNone(draft.text_content)
        self.assertIsNone(draft.text_length)
        self.assertIsNone(draft.author_texts_image_url)
        self.assertEqual((await self.client.get(f"/author_texts/{text_id}")).status_code, 404)
        await self.client.post("/author_texts/drafts", data={"work_title": "Повтор"})
        count = await self.session.scalar(select(func.count()).select_from(AuthorText).where(AuthorText.creator_id == author_texts_settings.author_texts_current_user_id))
        self.assertEqual(count, 1)

        page = await self.client.get("/author_texts/add")
        self.assertNotIn('type="file"', page.text)
        self.assertIn('>Опубликовать</button>', page.text)
        self.assertNotIn('None', page.text)
        self.assertIn('/author_texts-assets/media/author_texts_default.jpg', page.text)
        self.assertIn('/author_texts-assets/media/author_texts_default.webm', page.text)
        for asset in ("author_texts_default.jpg", "author_texts_default.webm"):
            response = await self.client.get(f"/author_texts-assets/media/{asset}")
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(response.content), 100)

        form = {"work_title": "Тестовый текст", "author_name": "Автор", "publication_year": "", "short_description": "Описание", "text_content": "Мир, мир! Война и мир."}
        response = await self.client.post(f"/author_texts/{text_id}/publish", data={**form, "text_content": " "})
        self.assertEqual(response.status_code, 422)
        response = await self.client.post(f"/author_texts/{text_id}/publish", data=form)
        self.assertEqual(response.status_code, 303)
        await self.session.refresh(draft)
        self.assertEqual((draft.text_length, draft.unique_token_count), (5, 3))
        self.assertEqual(draft.author_texts_status, AuthorTextStatus.PUBLISHED)
        self.assertIsNone(draft.publication_year)
        self.session.add(AuthorTextsLike(researcher_id=author_texts_settings.author_texts_current_user_id, author_text_id=text_id))
        await self.session.flush()
        self.session.expire(draft, ['likes'])
        feed = await self.client.get(f"/author_texts/{text_id}")
        self.assertEqual(feed.status_code, 200)
        self.assertIn('Отметок нравится: 1', feed.text)
        self.assertEqual((await self.client.get(f"/author_texts/{text_id}?next=true")).status_code, 200)

        grid = await self.client.get('/author_texts?min_text_length=6')
        self.assertNotIn(f'href="/author_texts/{text_id}"', grid.text)
        self.assertIn('Применено: 6 токенов', grid.text)
        self.assertNotIn('oninput=', grid.text)
        response = await self.client.post(f"/author_texts/{text_id}/delete")
        self.assertEqual(response.status_code, 303)
        await self.session.refresh(draft)
        self.assertEqual(draft.author_texts_status, AuthorTextStatus.DELETED)
        self.assertEqual((await self.client.get(f"/author_texts/{text_id}")).status_code, 404)
        self.assertEqual((await self.client.post(f"/author_texts/{text_id}/delete")).status_code, 404)
        grid = await self.client.get('/author_texts')
        self.assertNotIn(f'href="/author_texts/{text_id}"', grid.text)


class AuthorTextsTemplateTest(unittest.TestCase):
    def test_templates_contain_no_javascript(self):
        frontend = Path(author_texts_settings.author_texts_frontend_root)
        for template in (frontend / 'templates').glob('*.html'):
            html = template.read_text(encoding='utf-8').lower()
            self.assertNotIn('<script', html)
            self.assertNotRegex(html, r'\bon\w+\s*=')


if __name__ == "__main__":
    unittest.main()
