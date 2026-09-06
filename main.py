import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.handlers import router


PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = Path(
    os.getenv("FRONTEND_ROOT", PROJECT_DIR.parent / "lexical-diversity-frontend")
).resolve()

app = FastAPI(title="Lexical Diversity")

# CSS и локальные медиа для запуска без Docker.
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "public"), name="assets")
app.mount(
    "/media",
    StaticFiles(directory=FRONTEND_DIR / "minio-seed" / "media"),
    name="media",
)
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
