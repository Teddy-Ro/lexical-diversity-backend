import os
from pathlib import Path

import uvicorn
from api.ttr_handlers import ttr_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

TTR_PROJECT_DIR = Path(__file__).resolve().parent
TTR_FRONTEND_DIR = Path(
    os.getenv(
        "TTR_FRONTEND_ROOT",
        TTR_PROJECT_DIR.parent / "lexical-diversity-frontend",
    )
).resolve()

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

app = ttr_app


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
