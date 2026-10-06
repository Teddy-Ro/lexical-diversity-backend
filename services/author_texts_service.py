from fastapi import HTTPException, UploadFile
from models.author_texts_models import (
    AuthorText,
    AuthorTextsLike,
    AuthorTextStatus,
    AuthorTextsUser,
)
from repositories.author_texts_repository import AuthorTextsRepository
from schemas.author_texts_schemas import (
    AuthorTextsPublish,
    AuthorTextsRegistration,
    AuthorTextsResponse,
    AuthorTextsUserResponse,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from services.author_texts_media import AuthorTextsMedia, author_texts_media_url
from services.author_texts_passwords import hash_author_texts_password
from services.author_texts_statistics import calculate_author_texts_statistics


def serialize_author_texts(author_text: AuthorText) -> AuthorTextsResponse:
    ratio = None
    if (
        author_text.text_length is not None
        and author_text.unique_token_count is not None
    ):
        ratio = (
            author_text.unique_token_count / author_text.text_length
            if author_text.text_length
            else 0.0
        )
    return AuthorTextsResponse(
        author_text_id=author_text.author_text_id,
        work_title=author_text.work_title,
        author_name=author_text.author_name,
        publication_year=author_text.publication_year,
        short_description=author_text.short_description,
        text_content=author_text.text_content,
        author_texts_image_url=author_texts_media_url(
            author_text.author_texts_image_url
        ),
        author_texts_video_url=author_texts_media_url(
            author_text.author_texts_video_url
        ),
        unique_token_count=author_text.unique_token_count,
        text_length=author_text.text_length,
        author_texts_ratio=ratio,
        author_texts_like_count=len(author_text.likes),
    )


class AuthorTextsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AuthorTextsRepository(session)

    async def list_author_texts(self, min_text_length: int | None):
        return [
            serialize_author_texts(item)
            for item in await self.repository.list_published(min_text_length)
        ]

    async def get_author_texts_feed(self, author_text_id: int | None, next_text: bool):
        if author_text_id is None:
            selected = await self.repository.first_published()
        else:
            selected = await self.repository.published(author_text_id)
            if selected is not None and next_text:
                selected = (
                    await self.repository.first_published(author_text_id)
                    or await self.repository.first_published()
                )
        if selected is None:
            raise HTTPException(404)
        return serialize_author_texts(selected)

    async def get_author_texts_draft(self, user_id: int):
        draft = await self.repository.draft(user_id)
        if draft is None:
            raise HTTPException(404)
        return serialize_author_texts(draft)

    async def create_author_texts(
        self,
        user_id: int,
        work_title: str,
        image: UploadFile,
        video: UploadFile,
        media: AuthorTextsMedia,
    ):
        await media.validate(image, "image")
        await media.validate(video, "video")
        # Serialize concurrent creates for this user; the partial unique index is a second guard.
        if await self.repository.user(user_id, lock=True) is None:
            raise HTTPException(404)
        if await self.repository.draft(user_id) is not None:
            raise HTTPException(409)
        uploaded = []
        try:
            uploaded.append(await media.upload(image, "image"))
            uploaded.append(await media.upload(video, "video"))
            draft = AuthorText(
                work_title=work_title,
                creator_id=user_id,
                author_texts_status=AuthorTextStatus.DRAFT,
                author_texts_image_url=uploaded[0],
                author_texts_video_url=uploaded[1],
                likes=[],
            )
            self.session.add(draft)
            await self.session.flush()
            response = serialize_author_texts(draft)
            await self.session.commit()
            return response
        except Exception:
            await self.session.rollback()
            for key in uploaded:
                await media.remove(key)
            raise

    async def publish_author_texts(
        self, user_id: int, author_text_id: int, payload: AuthorTextsPublish
    ):
        draft = await self.repository.draft(user_id, lock=True)
        if draft is None or draft.author_text_id != author_text_id:
            raise HTTPException(404)
        statistics = calculate_author_texts_statistics(payload.text_content)
        if statistics.text_length == 0:
            raise HTTPException(422)
        for name, value in payload.model_dump().items():
            setattr(draft, name, value)
        draft.text_length = statistics.text_length
        draft.unique_token_count = statistics.unique_token_count
        draft.author_texts_status = AuthorTextStatus.PUBLISHED
        response = serialize_author_texts(draft)
        await self.session.commit()
        return response

    async def delete_author_texts(self, user_id: int, author_text_id: int):
        author_text = await self.repository.published(author_text_id, lock=True)
        if author_text is None or author_text.creator_id != user_id:
            raise HTTPException(404)
        author_text.author_texts_status = AuthorTextStatus.DELETED
        await self.session.commit()

    async def like_author_texts(self, user_id: int, author_text_id: int, value: int):
        author_text = await self.repository.published(author_text_id, lock=True)
        if author_text is None or await self.repository.user(user_id) is None:
            raise HTTPException(404)
        like = next(
            (item for item in author_text.likes if item.researcher_id == user_id), None
        )
        if value == 1 and like is None:
            author_text.likes.append(AuthorTextsLike(researcher_id=user_id))
        elif value == 0 and like is not None:
            # Delete only the link; reload the collection after flushing.
            await self.session.delete(like)
            await self.session.flush()
        await self.session.flush()
        author_text = await self.repository.published(author_text_id)
        response = serialize_author_texts(author_text)
        await self.session.commit()
        return response


class AuthorTextsUsersService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_author_texts_user(self, payload: AuthorTextsRegistration):
        user = AuthorTextsUser(
            username=payload.username,
            password_hash=await run_in_threadpool(
                hash_author_texts_password, payload.password
            ),
        )
        self.session.add(user)
        try:
            await self.session.flush()
            response = AuthorTextsUserResponse(
                author_texts_user_id=user.author_texts_user_id, username=user.username
            )
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise HTTPException(409) from error
        return response
