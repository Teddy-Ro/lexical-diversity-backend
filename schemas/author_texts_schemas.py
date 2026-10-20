"""API contracts: no HTTP status, lifecycle status or password hash in outputs."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

AuthorTextsTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class AuthorTextsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorTextsCreate(AuthorTextsInput):
    work_title: AuthorTextsTitle


class AuthorTextsPublish(AuthorTextsInput):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "work_title": "Проверка TTR", "short_description": "Пример авторского текста",
        "text_length": 5, "unique_token_count": 3,
    }})
    work_title: AuthorTextsTitle
    short_description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    text_length: Annotated[int, Field(strict=True, ge=1, le=2147483647)]
    unique_token_count: Annotated[int, Field(strict=True, ge=1, le=2147483647)]

    @model_validator(mode="after")
    def validate_token_counts(self):
        if self.unique_token_count > self.text_length:
            raise ValueError("Unique token count cannot exceed total token count")
        return self


class AuthorTextsLikeInput(AuthorTextsInput):
    value: Annotated[int, Field(strict=True, ge=0, le=1)]


class AuthorTextsRegistration(AuthorTextsInput):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "username": "author_texts_lab4", "password": "author_texts_demo",
    }})
    username: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class AuthorTextsUserResponse(BaseModel):
    author_texts_user_id: int
    username: str


class AuthorTextsLogin(AuthorTextsInput):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "username": "author_texts_lab4", "password": "author_texts_demo",
    }})
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class AuthorTextsResponse(BaseModel):
    author_text_id: int
    work_title: str
    short_description: str | None
    author_texts_image_url: str | None
    author_texts_video_url: str | None
    unique_token_count: int | None
    text_length: int | None
    author_texts_ratio: float | None
    author_texts_like_count: int
    is_owner: Annotated[int, Field(ge=0, le=1)]
    is_liked: Annotated[int, Field(ge=0, le=1)]
