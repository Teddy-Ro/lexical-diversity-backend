from pathlib import Path

from config.author_texts_settings import get_author_texts_settings
from db.author_texts_session import get_author_texts_session
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from models.author_texts_models import AuthorText, AuthorTextStatus
from services.author_texts_media import author_texts_media_url
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

author_texts_settings = get_author_texts_settings()
author_texts_router = APIRouter()
author_texts_templates = Jinja2Templates(
    directory=Path(author_texts_settings.author_texts_frontend_root).resolve()
    / "templates"
)
AUTHOR_TEXTS_DEFAULT_IMAGE_URL = "/author_texts-assets/media/author_texts_default.jpg"
AUTHOR_TEXTS_DEFAULT_VIDEO_URL = "/author_texts-assets/media/author_texts_default.webm"


def format_author_texts_compact_number(value: int) -> str:
    if value >= 1_000_000:
        compact_value, suffix = value / 1_000_000, "M"
    elif value >= 1_000:
        compact_value, suffix = value / 1_000, "K"
    else:
        return str(value)
    decimal_places = 0 if compact_value >= 100 else 1
    result = f"{compact_value:.{decimal_places}f}"
    return f"{result.rstrip('0').rstrip('.') if decimal_places else result}{suffix}"


def prepare_author_texts_text(author_texts_text: AuthorText) -> dict:
    ratio = (
        author_texts_text.unique_token_count / author_texts_text.text_length
        if author_texts_text.text_length
        and author_texts_text.unique_token_count is not None
        else 0
    )
    return {
        "author_text_id": author_texts_text.author_text_id,
        "work_title": author_texts_text.work_title,
        "short_description": author_texts_text.short_description,
        "author_texts_image_url": author_texts_media_url(
            author_texts_text.author_texts_image_url
        )
        or AUTHOR_TEXTS_DEFAULT_IMAGE_URL,
        "author_texts_video_url": author_texts_media_url(
            author_texts_text.author_texts_video_url
        )
        or AUTHOR_TEXTS_DEFAULT_VIDEO_URL,
        "unique_token_count": author_texts_text.unique_token_count,
        "text_length": author_texts_text.text_length,
        "compact_unique_token_count": format_author_texts_compact_number(
            author_texts_text.unique_token_count or 0
        ),
        "compact_text_length": format_author_texts_compact_number(
            author_texts_text.text_length or 0
        ),
        "author_texts_ratio": f"{ratio:.3f}",
        "author_texts_like_count": len(author_texts_text.likes),
    }


@author_texts_router.get("/", include_in_schema=False)
async def redirect_to_author_texts_grid():
    return RedirectResponse(url="/author_texts")


@author_texts_router.get("/author_texts", response_class=HTMLResponse)
async def show_author_texts_grid(
    request: Request,
    min_text_length: int | None = Query(default=None, ge=0),
    author_texts_session: AsyncSession = Depends(get_author_texts_session),
):
    conditions = [AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED]
    if min_text_length is not None:
        conditions.append(AuthorText.text_length >= min_text_length)
    author_texts = (
        await author_texts_session.scalars(
            select(AuthorText)
            .where(*conditions)
            .options(selectinload(AuthorText.likes))
            .order_by(AuthorText.author_text_id)
        )
    ).all()
    max_text_length = (
        await author_texts_session.scalar(
            select(func.max(AuthorText.text_length)).where(
                AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED
            )
        )
        or 0
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
    return author_texts_templates.TemplateResponse(
        request=request,
        name="author_texts_grid.html",
        context={
            "title": "TTR — корпус текстов",
            "author_texts_active_grid": True,
            "author_texts": [prepare_author_texts_text(item) for item in author_texts],
            "author_texts_feed_text_id": author_texts[0].author_text_id
            if author_texts
            else None,
            "min_text_length": min_text_length or 0,
            "max_text_length": max_text_length,
            "max_text_length_compact": format_author_texts_compact_number(
                max_text_length
            ),
            "text_length_ticks": [
                {"value": tick, "label": format_author_texts_compact_number(tick)}
                for tick in text_length_ticks
            ],
        },
    )


@author_texts_router.get("/author_texts/add", include_in_schema=False)
async def author_texts_add_api_documentation():
    return RedirectResponse("/api/docs")


@author_texts_router.get("/author_texts/{author_text_id}", response_class=HTMLResponse)
async def show_author_texts_feed(
    request: Request,
    author_text_id: int,
    show_next: bool = Query(default=False, alias="next"),
    author_texts_session: AsyncSession = Depends(get_author_texts_session),
):
    selected = await author_texts_session.scalar(
        select(AuthorText)
        .where(
            AuthorText.author_text_id == author_text_id,
            AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED,
        )
        .options(selectinload(AuthorText.likes))
    )
    if selected is None:
        raise HTTPException(404, "TTR-текст не найден")
    if show_next:
        next_text = await author_texts_session.scalar(
            select(AuthorText)
            .where(
                AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED,
                AuthorText.author_text_id > selected.author_text_id,
            )
            .options(selectinload(AuthorText.likes))
            .order_by(AuthorText.author_text_id)
            .limit(1)
        )
        if next_text is None:
            next_text = await author_texts_session.scalar(
                select(AuthorText)
                .where(AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED)
                .options(selectinload(AuthorText.likes))
                .order_by(AuthorText.author_text_id)
                .limit(1)
            )
        selected = next_text
    return author_texts_templates.TemplateResponse(
        request=request,
        name="author_texts_feed.html",
        context={
            "title": f"TTR — {selected.work_title}",
            "author_texts_active_feed": True,
            "author_texts_text": prepare_author_texts_text(selected),
            "author_texts_feed_text_id": selected.author_text_id,
        },
    )
