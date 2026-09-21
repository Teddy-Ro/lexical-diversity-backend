from pathlib import Path

import uvicorn
from api.ttr_handlers import ttr_router
from config.ttr_settings import get_ttr_settings
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

TTR_PROJECT_DIR = Path(__file__).resolve().parent
TTR_FRONTEND_DIR = Path(get_ttr_settings().ttr_frontend_root).resolve()

ttr_app = FastAPI(title="TTR — Type-Token Ratio")

ttr_app.mount(
    "/ttr-assets",
    StaticFiles(directory=TTR_FRONTEND_DIR / "public"),
    name="ttr-assets",
)
ttr_app.mount(
    "/ttr-media",
    StaticFiles(directory=TTR_FRONTEND_DIR / "minio-seed" / "media"),
    name="ttr-media",
)
ttr_app.include_router(ttr_router)

# Имя app оставлено как стандартная точка входа ASGI/Uvicorn.
app = ttr_app


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
