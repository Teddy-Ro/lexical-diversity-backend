from datetime import UTC, datetime
from pathlib import Path

from config.ttr_settings import get_ttr_settings
from db.ttr_session import get_ttr_session
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from models.ttr_models import TTRText, TTRTextStatus
from services.ttr_statistics import calculate_ttr_statistics
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

ttr_settings = get_ttr_settings()
ttr_router = APIRouter()
ttr_templates = Jinja2Templates(
    directory=Path(ttr_settings.ttr_frontend_root).resolve() / "templates"
)
TTR_DEFAULT_IMAGE_URL = "/ttr-media/ttr-turgenev-fathers-sons.jpg"


def format_ttr_compact_number(value: int) -> str:
    if value >= 1_000_000:
        compact_value, suffix = value / 1_000_000, "M"
    elif value >= 1_000:
        compact_value, suffix = value / 1_000, "K"
    else:
        return str(value)
    decimal_places = 0 if compact_value >= 100 else 1
    result = f"{compact_value:.{decimal_places}f}"
    return f"{result.rstrip('0').rstrip('.') if decimal_places else result}{suffix}"


def prepare_ttr_text(ttr_text: TTRText) -> dict:
    ratio = (
        ttr_text.unique_token_count / ttr_text.text_length
        if ttr_text.text_length
        else 0
    )
    return {
        "ttr_text_id": ttr_text.ttr_text_id,
        "work_title": ttr_text.work_title,
        "author_name": ttr_text.author_name,
        "publication_year": ttr_text.publication_year,
        "short_description": ttr_text.short_description,
        "text_content": ttr_text.text_content,
        "ttr_image_url": ttr_text.ttr_image_url or TTR_DEFAULT_IMAGE_URL,
        "ttr_video_url": ttr_text.ttr_video_url,
        "unique_token_count": ttr_text.unique_token_count,
        "text_length": ttr_text.text_length,
        "compact_unique_token_count": format_ttr_compact_number(
            ttr_text.unique_token_count
        ),
        "compact_text_length": format_ttr_compact_number(ttr_text.text_length),
        "ttr_ratio": f"{ratio:.3f}",
        "ttr_like_count": len(ttr_text.likes),
    }


def read_ttr_text_input(text_content: str) -> str:
    normalized_text = text_content.strip()
    if not normalized_text:
        raise HTTPException(422, "Введите текст произведения")
    return normalized_text


@ttr_router.get("/", include_in_schema=False)
async def redirect_to_ttr_grid():
    return RedirectResponse(url="/ttr-texts")


@ttr_router.get("/ttr-texts", response_class=HTMLResponse)
async def show_ttr_grid(
    request: Request,
    min_text_length: int | None = Query(default=None, ge=0),
    ttr_session: AsyncSession = Depends(get_ttr_session),
):
    conditions = [TTRText.ttr_status == TTRTextStatus.PUBLISHED]
    if min_text_length is not None:
        conditions.append(TTRText.text_length >= min_text_length)
    ttr_texts = (
        await ttr_session.scalars(
            select(TTRText)
            .where(*conditions)
            .options(selectinload(TTRText.likes))
            .order_by(TTRText.ttr_text_id)
        )
    ).all()
    max_text_length = (
        await ttr_session.scalar(
            select(func.max(TTRText.text_length)).where(
                TTRText.ttr_status == TTRTextStatus.PUBLISHED
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
    return ttr_templates.TemplateResponse(
        request=request,
        name="ttr_grid.html",
        context={
            "title": "TTR — корпус текстов",
            "ttr_active_grid": True,
            "ttr_texts": [prepare_ttr_text(item) for item in ttr_texts],
            "ttr_feed_text_id": ttr_texts[0].ttr_text_id if ttr_texts else None,
            "min_text_length": min_text_length or 0,
            "max_text_length": max_text_length,
            "max_text_length_compact": format_ttr_compact_number(max_text_length),
            "text_length_ticks": [
                {"value": tick, "label": format_ttr_compact_number(tick)}
                for tick in text_length_ticks
            ],
        },
    )


@ttr_router.get("/ttr-texts/add", response_class=HTMLResponse)
async def show_ttr_add(
    request: Request, ttr_session: AsyncSession = Depends(get_ttr_session)
):
    draft = await ttr_session.scalar(
        select(TTRText)
        .where(
            TTRText.creator_id == ttr_settings.ttr_current_user_id,
            TTRText.ttr_status == TTRTextStatus.DRAFT,
        )
        .options(selectinload(TTRText.likes))
    )
    first_published_id = await ttr_session.scalar(
        select(TTRText.ttr_text_id)
        .where(TTRText.ttr_status == TTRTextStatus.PUBLISHED)
        .order_by(TTRText.ttr_text_id)
        .limit(1)
    )
    return ttr_templates.TemplateResponse(
        request=request,
        name="ttr_add.html",
        context={
            "title": "TTR — добавление текста",
            "ttr_active_add": True,
            "ttr_text": prepare_ttr_text(draft) if draft else None,
            "ttr_feed_text_id": first_published_id,
        },
    )


@ttr_router.post("/ttr-texts/drafts")
async def create_ttr_text(
    work_title: str = Form(min_length=1, max_length=200),
    author_name: str = Form(min_length=1, max_length=200),
    publication_year: int | None = Form(default=None, ge=1, le=2100),
    short_description: str = Form(min_length=1, max_length=500),
    text_content: str = Form(min_length=1),
    ttr_session: AsyncSession = Depends(get_ttr_session),
):
    existing_draft = await ttr_session.scalar(
        select(TTRText.ttr_text_id).where(
            TTRText.creator_id == ttr_settings.ttr_current_user_id,
            TTRText.ttr_status == TTRTextStatus.DRAFT,
        )
    )
    if existing_draft:
        return RedirectResponse("/ttr-texts/add", status_code=status.HTTP_303_SEE_OTHER)
    normalized_text = read_ttr_text_input(text_content)
    statistics = calculate_ttr_statistics(normalized_text)
    ttr_text = TTRText(
        work_title=work_title.strip(),
        author_name=author_name.strip(),
        publication_year=publication_year,
        short_description=short_description.strip(),
        text_content=normalized_text,
        ttr_status=TTRTextStatus.PUBLISHED,
        unique_token_count=statistics.unique_token_count,
        text_length=statistics.text_length,
        published_at=datetime.now(UTC),
        creator_id=ttr_settings.ttr_current_user_id,
    )
    ttr_session.add(ttr_text)
    await ttr_session.commit()
    await ttr_session.refresh(ttr_text)
    return RedirectResponse(
        f"/ttr-texts/{ttr_text.ttr_text_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@ttr_router.post("/ttr-texts/{ttr_text_id}/publish")
async def publish_ttr_text(
    ttr_text_id: int,
    work_title: str = Form(min_length=1, max_length=200),
    author_name: str = Form(min_length=1, max_length=200),
    publication_year: int | None = Form(default=None, ge=1, le=2100),
    short_description: str = Form(min_length=1, max_length=500),
    text_content: str = Form(default=""),
    ttr_session: AsyncSession = Depends(get_ttr_session),
):
    draft = await ttr_session.scalar(
        select(TTRText).where(
            TTRText.ttr_text_id == ttr_text_id,
            TTRText.creator_id == ttr_settings.ttr_current_user_id,
            TTRText.ttr_status == TTRTextStatus.DRAFT,
        )
    )
    if draft is None:
        raise HTTPException(404, "Черновик не найден")
    normalized_text = read_ttr_text_input(text_content)
    statistics = calculate_ttr_statistics(normalized_text)
    draft.work_title = work_title.strip()
    draft.author_name = author_name.strip()
    draft.publication_year = publication_year
    draft.short_description = short_description.strip()
    draft.text_content = normalized_text
    draft.text_length = statistics.text_length
    draft.unique_token_count = statistics.unique_token_count
    draft.ttr_status = TTRTextStatus.PUBLISHED
    draft.published_at = datetime.now(UTC)
    await ttr_session.commit()
    return RedirectResponse(
        f"/ttr-texts/{draft.ttr_text_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@ttr_router.post("/ttr-texts/{ttr_text_id}/delete")
async def delete_ttr_text(
    ttr_text_id: int, ttr_session: AsyncSession = Depends(get_ttr_session)
):
    result = await ttr_session.execute(
        text(
            "UPDATE ttr_texts SET ttr_status = 'deleted' "
            "WHERE ttr_text_id = :ttr_text_id AND ttr_status = 'published'"
        ),
        {"ttr_text_id": ttr_text_id},
    )
    if result.rowcount == 0:
        await ttr_session.rollback()
        raise HTTPException(404, "Опубликованный текст не найден")
    await ttr_session.commit()
    return RedirectResponse("/ttr-texts", status_code=status.HTTP_303_SEE_OTHER)


@ttr_router.get("/ttr-texts/{ttr_text_id}", response_class=HTMLResponse)
async def show_ttr_feed(
    request: Request,
    ttr_text_id: int,
    show_next: bool = Query(default=False, alias="next"),
    ttr_session: AsyncSession = Depends(get_ttr_session),
):
    selected = await ttr_session.scalar(
        select(TTRText)
        .where(
            TTRText.ttr_text_id == ttr_text_id,
            TTRText.ttr_status == TTRTextStatus.PUBLISHED,
        )
        .options(selectinload(TTRText.likes))
    )
    if selected is None:
        raise HTTPException(404, "TTR-текст не найден")
    if show_next:
        next_text = await ttr_session.scalar(
            select(TTRText)
            .where(
                TTRText.ttr_status == TTRTextStatus.PUBLISHED,
                TTRText.ttr_text_id > selected.ttr_text_id,
            )
            .options(selectinload(TTRText.likes))
            .order_by(TTRText.ttr_text_id)
            .limit(1)
        )
        if next_text is None:
            next_text = await ttr_session.scalar(
                select(TTRText)
                .where(TTRText.ttr_status == TTRTextStatus.PUBLISHED)
                .options(selectinload(TTRText.likes))
                .order_by(TTRText.ttr_text_id)
                .limit(1)
            )
        selected = next_text
    return ttr_templates.TemplateResponse(
        request=request,
        name="ttr_feed.html",
        context={
            "title": f"TTR — {selected.work_title}",
            "ttr_active_feed": True,
            "ttr_text": prepare_ttr_text(selected),
            "ttr_feed_text_id": selected.ttr_text_id,
        },
    )
