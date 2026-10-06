"""Lab 3 REST API. HTML routes remain separate for the lab 2 demonstration."""

import logging
from typing import Annotated

from db.author_texts_session import get_author_texts_session
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from schemas.author_texts_schemas import (
    AuthorTextsCreate,
    AuthorTextsLikeInput,
    AuthorTextsPublish,
    AuthorTextsRegistration,
    AuthorTextsResponse,
    AuthorTextsUserResponse,
)
from services.author_texts_media import AuthorTextsMedia, get_author_texts_media
from services.author_texts_service import AuthorTextsService, AuthorTextsUsersService
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.author_texts_dependencies import (
    AuthorTextsCurrentUser,
    get_current_author_texts_user,
)

author_texts_api = FastAPI(title="Author texts — ЛР-3", version="3.0.0")
author_texts_api_router = APIRouter(prefix="/author_texts", tags=["author_texts"])
author_texts_users_router = APIRouter(
    prefix="/author_texts_users", tags=["author_texts_users"]
)


@author_texts_api.exception_handler(StarletteHTTPException)
async def author_texts_http_error(request: Request, error: StarletteHTTPException):
    return Response(status_code=error.status_code, headers=error.headers)


@author_texts_api.exception_handler(RequestValidationError)
async def author_texts_validation_error(
    request: Request, error: RequestValidationError
):
    return Response(status_code=422)


@author_texts_api.exception_handler(Exception)
async def author_texts_internal_error(request: Request, error: Exception):
    logging.getLogger(__name__).error("Author texts API failure", exc_info=error)
    return Response(status_code=500)


def get_author_texts_service(session: AsyncSession = Depends(get_author_texts_session)):
    return AuthorTextsService(session)


def get_author_texts_users_service(
    session: AsyncSession = Depends(get_author_texts_session),
):
    return AuthorTextsUsersService(session)


AuthorTextsActor = Annotated[
    AuthorTextsCurrentUser, Depends(get_current_author_texts_user)
]
AuthorTextsServiceDependency = Annotated[
    AuthorTextsService, Depends(get_author_texts_service)
]


@author_texts_api_router.get(
    "",
    response_model=list[AuthorTextsResponse],
    summary="Корпус опубликованных текстов",
)
async def list_author_texts(
    service: AuthorTextsServiceDependency,
    min_text_length: int | None = Query(None, ge=0),
):
    return await service.list_author_texts(min_text_length)


@author_texts_api_router.get(
    "/draft",
    response_model=AuthorTextsResponse,
    summary="Черновик текущего пользователя",
)
async def get_author_texts_draft(
    service: AuthorTextsServiceDependency, actor: AuthorTextsActor
):
    return await service.get_author_texts_draft(actor.author_texts_user_id)


@author_texts_api_router.get(
    "/{author_text_id}",
    response_model=AuthorTextsResponse,
    summary="Карточка по ID или следующая",
)
@author_texts_api_router.get(
    "/feed", response_model=AuthorTextsResponse, summary="Первая карточка ленты"
)
async def get_author_texts_feed(
    service: AuthorTextsServiceDependency,
    author_text_id: int | None = None,
    next_text: bool = Query(False, alias="next"),
):
    if author_text_id is not None and author_text_id < 1:
        raise HTTPException(422)
    return await service.get_author_texts_feed(author_text_id, next_text)


@author_texts_api_router.post(
    "",
    response_model=AuthorTextsResponse,
    status_code=201,
    summary="Создать черновик с фото и видео",
)
async def create_author_texts(
    request: Request,
    service: AuthorTextsServiceDependency,
    actor: AuthorTextsActor,
    work_title: str = Form(min_length=1, max_length=200),
    author_texts_image: UploadFile = File(),
    author_texts_video: UploadFile = File(),
    media: AuthorTextsMedia = Depends(get_author_texts_media),
):
    form = await request.form()
    allowed = {"work_title", "author_texts_image", "author_texts_video"}
    if set(form) != allowed or any(len(form.getlist(key)) != 1 for key in allowed):
        raise HTTPException(422)
    try:
        payload = AuthorTextsCreate(work_title=work_title)
    except ValidationError as error:
        raise HTTPException(422) from error
    return await service.create_author_texts(
        actor.author_texts_user_id,
        payload.work_title,
        author_texts_image,
        author_texts_video,
        media,
    )


@author_texts_api_router.put(
    "/{author_text_id}/publish",
    response_model=AuthorTextsResponse,
    summary="Заполнить и опубликовать собственный черновик",
)
async def publish_author_texts(
    author_text_id: int,
    payload: AuthorTextsPublish,
    service: AuthorTextsServiceDependency,
    actor: AuthorTextsActor,
):
    return await service.publish_author_texts(
        actor.author_texts_user_id, author_text_id, payload
    )


@author_texts_api_router.delete(
    "/{author_text_id}",
    response_class=Response,
    summary="Логически удалить собственный текст",
)
async def delete_author_texts(
    author_text_id: int, service: AuthorTextsServiceDependency, actor: AuthorTextsActor
):
    await service.delete_author_texts(actor.author_texts_user_id, author_text_id)
    return Response(status_code=200)


@author_texts_api_router.post(
    "/{author_text_id}/like",
    response_model=AuthorTextsResponse,
    summary="Поставить (1) или снять (0) лайк",
)
async def like_author_texts(
    author_text_id: int,
    payload: AuthorTextsLikeInput,
    service: AuthorTextsServiceDependency,
    actor: AuthorTextsActor,
):
    return await service.like_author_texts(
        actor.author_texts_user_id, author_text_id, payload.value
    )


@author_texts_users_router.post(
    "/register",
    response_model=AuthorTextsUserResponse,
    status_code=201,
    summary="Регистрация пользователя",
)
async def register_author_texts_user(
    payload: AuthorTextsRegistration,
    service: AuthorTextsUsersService = Depends(get_author_texts_users_service),
):
    return await service.register_author_texts_user(payload)


@author_texts_users_router.post(
    "/login", response_class=Response, summary="Вход — заглушка ЛР-3"
)
async def login_author_texts_user():
    return Response(status_code=200)


@author_texts_users_router.post(
    "/logout", response_class=Response, summary="Выход — заглушка ЛР-3"
)
async def logout_author_texts_user():
    return Response(status_code=200)


author_texts_api.include_router(author_texts_api_router)
author_texts_api.include_router(author_texts_users_router)

author_texts_openapi = author_texts_api.openapi


def get_author_texts_openapi():
    schema = author_texts_openapi()
    for path in schema["paths"].values():
        for operation in path.values():
            for code in ("404", "409", "422", "503"):
                operation["responses"][code] = {
                    "description": "HTTP error; empty response body"
                }
    return schema


author_texts_api.openapi = get_author_texts_openapi
