from pathlib import Path

from config.author_texts_settings import get_author_texts_settings
from db.author_texts_session import get_author_texts_session
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from models.author_texts_models import AuthorText, AuthorTextStatus
from services.author_texts_statistics import calculate_author_texts_statistics
from sqlalchemy import func, select, text
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
        "author_name": author_texts_text.author_name,
        "publication_year": author_texts_text.publication_year,
        "short_description": author_texts_text.short_description,
        "text_content": author_texts_text.text_content,
        "author_texts_image_url": author_texts_text.author_texts_image_url
        or AUTHOR_TEXTS_DEFAULT_IMAGE_URL,
        "author_texts_video_url": author_texts_text.author_texts_video_url
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


def read_author_texts_text_input(text_content: str) -> str:
    normalized_text = text_content.strip()
    if not normalized_text:
        raise HTTPException(422, "Введите текст произведения")
    return normalized_text


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


@author_texts_router.get("/author_texts/add", response_class=HTMLResponse)
async def show_author_texts_add(
    request: Request,
    author_texts_session: AsyncSession = Depends(get_author_texts_session),
):
    draft = await author_texts_session.scalar(
        select(AuthorText)
        .where(
            AuthorText.creator_id == author_texts_settings.author_texts_current_user_id,
            AuthorText.author_texts_status == AuthorTextStatus.DRAFT,
        )
        .options(selectinload(AuthorText.likes))
    )
    first_published_id = await author_texts_session.scalar(
        select(AuthorText.author_text_id)
        .where(AuthorText.author_texts_status == AuthorTextStatus.PUBLISHED)
        .order_by(AuthorText.author_text_id)
        .limit(1)
    )
    return author_texts_templates.TemplateResponse(
        request=request,
        name="author_texts_add.html",
        context={
            "title": "TTR — добавление текста",
            "author_texts_active_add": True,
            "author_texts_text": prepare_author_texts_text(draft) if draft else None,
            "author_texts_default_image_url": AUTHOR_TEXTS_DEFAULT_IMAGE_URL,
            "author_texts_default_video_url": AUTHOR_TEXTS_DEFAULT_VIDEO_URL,
            "author_texts_feed_text_id": first_published_id,
        },
    )


@author_texts_router.post("/author_texts/drafts")
async def create_author_texts_text(
    work_title: str = Form(min_length=1, max_length=200),
    author_texts_session: AsyncSession = Depends(get_author_texts_session),
):
    existing_draft = await author_texts_session.scalar(
        select(AuthorText.author_text_id).where(
            AuthorText.creator_id == author_texts_settings.author_texts_current_user_id,
            AuthorText.author_texts_status == AuthorTextStatus.DRAFT,
        )
    )
    if existing_draft:
        return RedirectResponse(
            "/author_texts/add", status_code=status.HTTP_303_SEE_OTHER
        )
    title = work_title.strip()
    if not title:
        raise HTTPException(422, "Введите название произведения")
    author_texts_text = AuthorText(
        work_title=title,
        author_texts_status=AuthorTextStatus.DRAFT,
        creator_id=author_texts_settings.author_texts_current_user_id,
    )
    author_texts_session.add(author_texts_text)
    await author_texts_session.commit()
    await author_texts_session.refresh(author_texts_text)
    return RedirectResponse(
        "/author_texts/add",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@author_texts_router.post("/author_texts/{author_text_id}/publish")
async def publish_author_texts_text(
    author_text_id: int,
    work_title: str = Form(min_length=1, max_length=200),
    author_name: str = Form(min_length=1, max_length=200),
    publication_year: int | None = Form(default=None, ge=1, le=2100),
    short_description: str = Form(min_length=1, max_length=500),
    text_content: str = Form(default=""),
    author_texts_session: AsyncSession = Depends(get_author_texts_session),
):
    draft = await author_texts_session.scalar(
        select(AuthorText).where(
            AuthorText.author_text_id == author_text_id,
            AuthorText.creator_id == author_texts_settings.author_texts_current_user_id,
            AuthorText.author_texts_status == AuthorTextStatus.DRAFT,
        )
    )
    if draft is None:
        raise HTTPException(404, "Черновик не найден")
    if (
        not work_title.strip()
        or not author_name.strip()
        or not short_description.strip()
    ):
        raise HTTPException(422, "Заполните название, автора и краткое описание")
    normalized_text = read_author_texts_text_input(text_content)
    statistics = calculate_author_texts_statistics(normalized_text)
    draft.work_title = work_title.strip()
    draft.author_name = author_name.strip()
    draft.publication_year = publication_year
    draft.short_description = short_description.strip()
    draft.text_content = normalized_text
    draft.text_length = statistics.text_length
    draft.unique_token_count = statistics.unique_token_count
    draft.author_texts_status = AuthorTextStatus.PUBLISHED
    await author_texts_session.commit()
    return RedirectResponse(
        f"/author_texts/{draft.author_text_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@author_texts_router.post("/author_texts/{author_text_id}/delete")
async def delete_author_texts_text(
    author_text_id: int,
    author_texts_session: AsyncSession = Depends(get_author_texts_session),
):
    result = await author_texts_session.execute(
        text(
            "UPDATE author_texts SET author_texts_status = 'deleted' "
            "WHERE author_text_id = :author_text_id AND author_texts_status = 'published'"
        ),
        {"author_text_id": author_text_id},
    )
    if result.rowcount == 0:
        await author_texts_session.rollback()
        raise HTTPException(404, "Опубликованный текст не найден")
    await author_texts_session.commit()
    return RedirectResponse("/author_texts", status_code=status.HTTP_303_SEE_OTHER)


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
