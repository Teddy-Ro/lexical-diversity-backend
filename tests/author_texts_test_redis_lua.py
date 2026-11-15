"""Read-only Lua scripts against real Redis; fixtures use unique session keys."""
import json
import os
import secrets
import unittest
from pathlib import Path

from redis.exceptions import ResponseError

from services.author_texts_sessions import (
    AUTHOR_TEXTS_SESSION_PREFIX,
    create_author_texts_redis,
)


@unittest.skipUnless(
    os.getenv("AUTHOR_TEXTS_RUN_REDIS_TESTS") == "1"
    or os.getenv("AUTHOR_TEXTS_RUN_DB_TESTS") == "1",
    "Redis integration test",
)
class AuthorTextsRedisLuaTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis = create_author_texts_redis()
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        self.get_script = (scripts / "author_texts_session_get.lua").read_text(encoding="utf-8")
        self.list_script = (scripts / "author_texts_sessions_list.lua").read_text(encoding="utf-8")
        self.keys = [AUTHOR_TEXTS_SESSION_PREFIX + secrets.token_urlsafe(32) for _ in range(3)]
        self.values = ["144", "145"]
        for key, value in zip(self.keys, self.values):
            await self.redis.set(key, value, ex=120)

    async def asyncTearDown(self):
        try:
            await self.redis.delete(*self.keys)
        finally:
            await self.redis.aclose()

    async def test_get_active_session(self):
        result = json.loads(await self.redis.eval(self.get_script, 1, self.keys[0]))
        self.assertEqual(result["session_key"], self.keys[0])
        self.assertEqual(result["user_id"], "144")
        self.assertGreater(result["ttl_seconds"], 0)

    async def test_get_missing_session(self):
        result = json.loads(await self.redis.eval(self.get_script, 1, self.keys[2]))
        self.assertEqual(result, {
            "session_key": self.keys[2], "user_id": None, "ttl_seconds": -2,
        })

    async def test_list_skips_missing_and_returns_empty_array(self):
        result = json.loads(await self.redis.eval(self.list_script, len(self.keys), *self.keys))
        self.assertEqual([row["user_id"] for row in result], self.values)
        self.assertEqual([row["session_key"] for row in result], self.keys[:2])
        self.assertTrue(all(row["ttl_seconds"] > 0 for row in result))
        self.assertEqual(json.loads(await self.redis.eval(self.list_script, 0)), [])

    async def test_values_and_expiration_are_not_changed(self):
        before = [await self.redis.ttl(key) for key in self.keys[:2]]
        await self.redis.eval(self.get_script, 1, self.keys[0])
        await self.redis.eval(self.list_script, 2, *self.keys[:2])
        self.assertEqual(await self.redis.mget(self.keys[:2]), self.values)
        after = [await self.redis.ttl(key) for key in self.keys[:2]]
        self.assertTrue(all(0 < new <= old for new, old in zip(after, before)))

    async def test_keys_outside_session_namespace_are_rejected(self):
        for script in (self.get_script, self.list_script):
            with self.assertRaises(ResponseError):
                await self.redis.eval(script, 1, "another_application:key")
        with self.assertRaises(ResponseError):
            await self.redis.eval(self.get_script, 0)
