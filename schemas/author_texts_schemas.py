"""API contracts: no HTTP status, lifecycle status or password hash in outputs."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

AuthorTextsTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class AuthorTextsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorTextsCreate(AuthorTextsInput):
    work_title: AuthorTextsTitle


class AuthorTextsPublish(AuthorTextsInput):
    work_title: AuthorTextsTitle
    author_name: AuthorTextsTitle
    publication_year: int | None = Field(default=None, ge=1, le=2100)
    short_description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    text_content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AuthorTextsLikeInput(AuthorTextsInput):
    value: Annotated[int, Field(strict=True, ge=0, le=1)]


class AuthorTextsRegistration(AuthorTextsInput):
    username: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class AuthorTextsUserResponse(BaseModel):
    author_texts_user_id: int
    username: str


class AuthorTextsResponse(BaseModel):
    author_text_id: int
    work_title: str
    author_name: str | None
    publication_year: int | None
    short_description: str | None
    text_content: str | None
    author_texts_image_url: str | None
    author_texts_video_url: str | None
    unique_token_count: int | None
    text_length: int | None
    author_texts_ratio: float | None
    author_texts_like_count: int
