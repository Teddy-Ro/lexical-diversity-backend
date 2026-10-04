from pathlib import Path

import uvicorn
from api.author_texts_handlers import author_texts_router
from config.author_texts_settings import get_author_texts_settings
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

AUTHOR_TEXTS_PROJECT_DIR = Path(__file__).resolve().parent
AUTHOR_TEXTS_FRONTEND_DIR = Path(get_author_texts_settings().author_texts_frontend_root).resolve()

author_texts_app = FastAPI(title="TTR — Type-Token Ratio")

author_texts_app.mount(
    "/author_texts-assets",
    StaticFiles(directory=AUTHOR_TEXTS_FRONTEND_DIR / "public"),
    name="author_texts-assets",
)
author_texts_app.include_router(author_texts_router)

app = author_texts_app


if __name__ == "__main__":
    uvicorn.run("author_texts_main:app", host="127.0.0.1", port=8000)
