import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from data.collections import AUTHOR_TEXTS


PROJECT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = Path(
    os.getenv("FRONTEND_ROOT", PROJECT_DIR.parent / "lexical-diversity-frontend")
).resolve()

router = APIRouter()
templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")


def text_for_page(author_text: dict) -> dict:
    """Добавляет вычисляемые поля, не меняя исходную коллекцию."""
    result = author_text.copy()
    ttr = author_text["unique_type_count"] / author_text["token_count"]
    result["like_count"] = len(author_text["liked_by_researcher_ids"])
    result["ttr"] = f"{ttr:.3f}"
    result["ttr_percent"] = f"{ttr * 100:.1f}%"
    return result


@router.get("/author-texts", response_class=HTMLResponse)
def show_text_grid(
    request: Request,
    min_unique_words: int | None = Query(default=None, ge=0),
):
    author_texts = [
        text_for_page(author_text)
        for author_text in AUTHOR_TEXTS
        if author_text["status"] == "published"
        and (
            min_unique_words is None
            or author_text["unique_type_count"] >= min_unique_words
        )
    ]

    return templates.TemplateResponse(
        request=request,
        name="grid.html",
        context={
            "title": "Корпус текстов",
            "active_grid": True,
            "author_texts": author_texts,
            "min_unique_words": min_unique_words if min_unique_words is not None else "",
        },
    )


@router.get("/author-texts/draft", response_class=HTMLResponse)
def show_text_draft(request: Request):
    draft = next(
        (author_text for author_text in AUTHOR_TEXTS if author_text["status"] == "draft"),
        None,
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="Черновик не найден")

    return templates.TemplateResponse(
        request=request,
        name="draft.html",
        context={
            "title": "Добавление текста",
            "active_draft": True,
            "author_text": text_for_page(draft),
        },
    )


@router.get("/author-texts/{author_text_id}", response_class=HTMLResponse)
def show_text_feed(
    request: Request,
    author_text_id: int,
    show_next: bool = Query(default=False, alias="next"),
):
    published = [
        author_text
        for author_text in AUTHOR_TEXTS
        if author_text["status"] == "published"
    ]
    author_text = next(
        (item for item in published if item["id"] == author_text_id),
        None,
    )
    if author_text is None:
        raise HTTPException(status_code=404, detail="Текст не найден")

    if show_next:
        current_index = published.index(author_text)
        author_text = published[(current_index + 1) % len(published)]

    return templates.TemplateResponse(
        request=request,
        name="feed.html",
        context={
            "title": "Лента текстов",
            "active_feed": True,
            "author_text": text_for_page(author_text),
        },
    )
