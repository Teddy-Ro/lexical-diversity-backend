"""Authentication against real Redis and transactional PostgreSQL fixtures."""

import os
import unittest

import httpx
from sqlalchemy import select

from api.author_texts_api import author_texts_api
from api.author_texts_dependencies import get_current_author_texts_user
from author_texts_main import app
from models.author_texts_models import AuthorText, AuthorTextsUser
from services.author_texts_passwords import hash_author_texts_password
from services.author_texts_sessions import (
    AuthorTextsSessions, AUTHOR_TEXTS_SESSION_PREFIX, create_author_texts_redis,
    get_author_texts_sessions,
)
from tests import author_texts_test_api as api_fixtures


@unittest.skipUnless(os.getenv("AUTHOR_TEXTS_RUN_DB_TESTS") == "1", "PostgreSQL and Redis integration test")
class AuthorTextsAuthTest(unittest.IsolatedAsyncioTestCase):
    # Reuse fixtures, not the lab-3 actor override: all requests authenticate with cookies.
    files = api_fixtures.AuthorTextsApiFlowTest.files
    create = api_fixtures.AuthorTextsApiFlowTest.create

    async def asyncSetUp(self):
        await api_fixtures.AuthorTextsApiFlowTest.asyncSetUp(self)
        author_texts_api.dependency_overrides.pop(get_current_author_texts_user)
        self.redis = create_author_texts_redis()
        self.sessions = AuthorTextsSessions(self.redis)
        self.cookie = self.settings.author_texts_session_cookie
        self.tokens = set()
        self.user.password_hash = hash_author_texts_password("test-password")
        self.other.password_hash = hash_author_texts_password("test-password")
        await self.session.flush()
        author_texts_api.dependency_overrides[get_author_texts_sessions] = lambda: self.sessions

    async def asyncTearDown(self):
        for token in self.tokens:
            await self.sessions.destroy(token)
        await self.redis.aclose()
        await api_fixtures.AuthorTextsApiFlowTest.asyncTearDown(self)

    def client_for_actor(self):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def login(self, user=None, client=None):
        user = user or self.user
        client = client or self.client
        response = await client.post("/api/author_texts_users/login", json={
            "username": user.username, "password": "test-password",
        })
        self.assertEqual(response.status_code, 200, response.text)
        token = client.cookies.get(self.cookie)
        self.assertIsNotNone(token)
        self.tokens.add(token)
        self.assertEqual(set(response.json()), {"author_texts_user_id", "username"})
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=lax", response.headers["set-cookie"])
        self.assertIn("Path=/api", response.headers["set-cookie"])
        return token

    async def test_guest_and_protected_endpoints(self):
        response = await self.client.get("/api/author_texts")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(x["is_owner"] == x["is_liked"] == 0 for x in response.json()))
        for method, path, kwargs in (
            ("get", "/api/author_texts/draft", {}),
            ("post", "/api/author_texts", {"data":{"work_title":"Test"}, "files":self.files()}),
            ("put", "/api/author_texts/1/publish", {"json":self.payload}),
            ("delete", "/api/author_texts/1", {}),
            ("post", "/api/author_texts/1/like", {"json":{"value":1}}),
        ):
            response = await getattr(self.client, method)(path, **kwargs)
            self.assertEqual((response.status_code, response.content), (401, b""))
        for token in ("garbage", "x" * 43):
            self.client.cookies.clear()
            self.client.cookies.set(self.cookie, token)
            self.assertEqual((await self.client.get("/api/author_texts")).status_code, 200)
            self.assertEqual((await self.client.get("/api/author_texts/draft")).status_code, 401)

    async def test_sessions_ownership_flags_and_logout(self):
        token = await self.login()
        key = AUTHOR_TEXTS_SESSION_PREFIX + token
        self.assertEqual(await self.redis.get(key), str(self.user.author_texts_user_id))
        self.assertGreater(await self.redis.ttl(key), 0)
        draft = await self.create()
        text_id = draft["author_text_id"]
        row = await self.session.get(AuthorText, text_id)
        self.assertEqual(row.creator_id, self.user.author_texts_user_id)
        self.assertIsNotNone(row.created_at)
        self.assertIsNone(row.published_at)
        async with self.client_for_actor() as other:
            await self.login(self.other, other)
            self.assertEqual((await other.get("/api/author_texts/draft")).status_code, 404)
            response = await other.put(f"/api/author_texts/{text_id}/publish", json=self.payload)
            self.assertEqual(response.status_code, 404)
            published = await self.client.put(f"/api/author_texts/{text_id}/publish", json=self.payload)
            self.assertEqual(published.status_code, 200)
            await self.session.refresh(row)
            self.assertIsNotNone(row.published_at)
            self.assertEqual((await other.delete(f"/api/author_texts/{text_id}")).status_code, 404)
            await other.post(f"/api/author_texts/{text_id}/like", json={"value":1})
            url=f"/api/author_texts/feed?author_text_id={text_id}"
            own = (await self.client.get(url)).json()
            foreign = (await other.get(url)).json()
            self.assertEqual((own["is_owner"], own["is_liked"]), (1, 0))
            self.assertEqual((foreign["is_owner"], foreign["is_liked"]), (0, 1))
        response = await self.client.post("/api/author_texts_users/logout")
        self.assertEqual((response.status_code, response.content), (200, b""))
        self.assertIsNone(await self.redis.get(key))
        self.assertIsNone(self.client.cookies.get(self.cookie))
        # Replay a copied cookie after logout; Redis must reject it.
        self.client.cookies.set(self.cookie, token)
        self.assertEqual((await self.client.get("/api/author_texts/draft")).status_code, 401)
        self.assertEqual((await self.client.get("/api/author_texts")).status_code, 200)

    async def test_password_errors_rotation_and_expiry(self):
        for username, password in ((self.user.username, "wrong"), ("missing-user", "wrong")):
            response = await self.client.post("/api/author_texts_users/login", json={"username":username,"password":password})
            self.assertEqual((response.status_code, response.content), (401, b""))
            self.assertNotIn("set-cookie", response.headers)
        first = await self.login()
        second = await self.login()
        self.assertNotEqual(first, second)
        self.assertIsNone(await self.redis.get(AUTHOR_TEXTS_SESSION_PREFIX + first))
        await self.redis.pexpire(AUTHOR_TEXTS_SESSION_PREFIX + second, 1)
        import asyncio
        await asyncio.sleep(0.02)
        self.assertEqual((await self.client.get("/api/author_texts/draft")).status_code, 401)

    async def test_registration_then_login(self):
        response = await self.client.post("/api/author_texts_users/register", json={
            "username":self.user.username + "_new", "password":"new-password",
        })
        self.assertEqual(response.status_code, 201)
        user_id=response.json()["author_texts_user_id"]
        response=await self.client.post("/api/author_texts_users/login", json={
            "username":self.user.username + "_new", "password":"new-password",
        })
        self.assertEqual(response.status_code, 200)
        token=self.client.cookies.get(self.cookie)
        self.tokens.add(token)
        self.assertEqual(await self.sessions.user_id(token), user_id)
        self.assertNotEqual(user_id, 1)

    async def test_origin_and_legacy_write_bypass(self):
        await self.login()
        response = await self.client.post("/api/author_texts_users/logout", headers={"Origin":"http://evil.example"})
        self.assertEqual((response.status_code, response.content), (403, b""))
        self.assertEqual((await self.client.get("/api/author_texts/draft")).status_code, 404)
        for path in ("/author_texts/drafts", "/author_texts/1/publish", "/author_texts/1/delete"):
            response=await self.client.post(path, data={"work_title":"bypass"})
            self.assertIn(response.status_code, (404, 405))
        response=await self.client.get("/author_texts/add")
        self.assertNotEqual(response.status_code, 200)
