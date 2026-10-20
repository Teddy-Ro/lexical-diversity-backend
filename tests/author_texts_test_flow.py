"""Public SSR is read-only in lab 4; personal operations use authenticated API."""
import unittest
from pathlib import Path
import httpx
from author_texts_main import app
from config.author_texts_settings import get_author_texts_settings


class AuthorTextsLegacyAccessTest(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_user_write_routes_are_not_exposed(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for path in ("/author_texts/drafts", "/author_texts/1/publish", "/author_texts/1/delete"):
                response = await client.post(path, data={"work_title": "bypass"})
                self.assertIn(response.status_code, (404, 405))
            response = await client.get("/author_texts/add")
            self.assertNotEqual(response.status_code, 200)


class AuthorTextsTemplateTest(unittest.TestCase):
    def test_templates_contain_no_javascript(self):
        frontend = Path(get_author_texts_settings().author_texts_frontend_root)
        for template in (frontend / "templates").glob("*.html"):
            html = template.read_text(encoding="utf-8").lower()
            self.assertNotIn("<script", html)
            self.assertNotRegex(html, r"\bon\w+\s*=")
