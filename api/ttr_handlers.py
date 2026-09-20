import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from data.ttr_collections import TTR_TEXTS

TTR_PROJECT_DIR = Path(__file__).resolve().parents[1]
TTR_FRONTEND_DIR = Path(
    os.getenv(
        "TTR_FRONTEND_ROOT",
        TTR_PROJECT_DIR.parent / "lexical-diversity-frontend",
    )
).resolve()

ttr_router = APIRouter()
ttr_templates = Jinja2Templates(directory=TTR_FRONTEND_DIR / "templates")


def format_ttr_compact_number(value: int) -> str:
    """Форматирует большие показатели для узкой боковой панели."""
    if value >= 1_000_000:
        compact_value = value / 1_000_000
        suffix = "M"
    elif value >= 1_000:
        compact_value = value / 1_000
        suffix = "K"
    else:
        return str(value)

    decimal_places = 0 if compact_value >= 100 else 1
    formatted_value = f"{compact_value:.{decimal_places}f}"
    if decimal_places:
        formatted_value = formatted_value.rstrip("0").rstrip(".")
    return f"{formatted_value}{suffix}"


def prepare_ttr_text(ttr_text: dict) -> dict:
    """Добавляет вычисляемые TTR-поля, не изменяя исходную коллекцию."""
    prepared_ttr_text = ttr_text.copy()
    ttr_ratio = ttr_text["unique_token_count"] / ttr_text["text_length"]
    prepared_ttr_text["ttr_like_count"] = len(
        ttr_text["liked_by_researcher_ids"]
    )
    prepared_ttr_text["ttr_ratio"] = f"{ttr_ratio:.3f}"
    prepared_ttr_text["compact_unique_token_count"] = format_ttr_compact_number(
        ttr_text["unique_token_count"]
    )
    prepared_ttr_text["compact_text_length"] = format_ttr_compact_number(
        ttr_text["text_length"]
    )
    return prepared_ttr_text


@ttr_router.get("/", include_in_schema=False)
def redirect_to_ttr_grid():
    return RedirectResponse(url="/ttr-texts")


@ttr_router.get("/ttr-texts", response_class=HTMLResponse)
def show_ttr_grid(
    request: Request,
    min_text_length: int | None = Query(default=None, ge=0),
):
    published_ttr_texts = [
        ttr_text
        for ttr_text in TTR_TEXTS
        if ttr_text["ttr_status"] == "published"
    ]
    filtered_ttr_texts = [
        prepare_ttr_text(ttr_text)
        for ttr_text in published_ttr_texts
        if min_text_length is None
        or ttr_text["text_length"] >= min_text_length
    ]
    max_text_length = max(
        ttr_text["text_length"] for ttr_text in published_ttr_texts
    )
    text_length_ticks = sorted(
        {
            0,
            round(max_text_length * 0.25 / 1_000) * 1_000,
            round(max_text_length * 0.5 / 1_000) * 1_000,
            round(max_text_length * 0.75 / 1_000) * 1_000,
            max_text_length,
        }
    )

    return ttr_templates.TemplateResponse(
        request=request,
        name="ttr_grid.html",
        context={
            "title": "TTR — корпус текстов",
            "ttr_active_grid": True,
            "ttr_texts": filtered_ttr_texts,
            "min_text_length": min_text_length or 0,
            "max_text_length": max_text_length,
            "max_text_length_compact": format_ttr_compact_number(max_text_length),
            "text_length_ticks": [
                {
                    "value": tick,
                    "label": format_ttr_compact_number(tick),
                }
                for tick in text_length_ticks
            ],
        },
    )


@ttr_router.get("/ttr-texts/add", response_class=HTMLResponse)
def show_ttr_add(request: Request):
    draft_ttr_text = next(
        (
            ttr_text
            for ttr_text in TTR_TEXTS
            if ttr_text["ttr_status"] == "draft"
        ),
        None,
    )
    if draft_ttr_text is None:
        raise HTTPException(status_code=404, detail="TTR-черновик не найден")

    return ttr_templates.TemplateResponse(
        request=request,
        name="ttr_add.html",
        context={
            "title": "TTR — добавление текста",
            "ttr_active_add": True,
            "ttr_text": prepare_ttr_text(draft_ttr_text),
        },
    )


@ttr_router.get("/ttr-texts/{ttr_text_id}", response_class=HTMLResponse)
def show_ttr_feed(
    request: Request,
    ttr_text_id: int,
    show_next: bool = Query(default=False, alias="next"),
):
    published_ttr_texts = [
        ttr_text
        for ttr_text in TTR_TEXTS
        if ttr_text["ttr_status"] == "published"
    ]
    selected_ttr_text = next(
        (
            ttr_text
            for ttr_text in published_ttr_texts
            if ttr_text["ttr_text_id"] == ttr_text_id
        ),
        None,
    )
    if selected_ttr_text is None:
        raise HTTPException(status_code=404, detail="TTR-текст не найден")

    if show_next:
        current_index = published_ttr_texts.index(selected_ttr_text)
        selected_ttr_text = published_ttr_texts[
            (current_index + 1) % len(published_ttr_texts)
        ]

    return ttr_templates.TemplateResponse(
        request=request,
        name="ttr_feed.html",
        context={
            "title": f"TTR — {selected_ttr_text['work_title']}",
            "ttr_active_feed": True,
            "ttr_text": prepare_ttr_text(selected_ttr_text),
        },
    )
