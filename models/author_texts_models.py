from enum import StrEnum

from db.author_texts_base import AuthorTextsBase
from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AuthorTextStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DELETED = "deleted"


class AuthorTextsUser(AuthorTextsBase):
    __tablename__ = "author_texts_users"

    author_texts_user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    texts: Mapped[list["AuthorText"]] = relationship(back_populates="creator")
    likes: Mapped[list["AuthorTextsLike"]] = relationship(back_populates="researcher")


class AuthorText(AuthorTextsBase):
    __tablename__ = "author_texts"
    __table_args__ = (
        CheckConstraint("text_length >= 0", name="ck_author_texts_text_length_nonnegative"),
        CheckConstraint(
            "unique_token_count >= 0",
            name="ck_author_texts_unique_token_count_nonnegative",
        ),
        CheckConstraint(
            "publication_year IS NULL OR publication_year BETWEEN 1 AND 2100",
            name="ck_author_texts_publication_year",
        ),
        Index(
            "uq_author_texts_one_draft_per_user",
            "creator_id",
            unique=True,
            postgresql_where=text("author_texts_status = 'draft'"),
        ),
    )

    author_text_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_title: Mapped[str] = mapped_column(String(200), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(200))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    short_description: Mapped[str | None] = mapped_column(String(500))
    text_content: Mapped[str | None] = mapped_column(Text)
    author_texts_status: Mapped[AuthorTextStatus] = mapped_column(
        Enum(
            AuthorTextStatus,
            name="author_texts_text_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=AuthorTextStatus.DRAFT,
        nullable=False,
    )
    author_texts_image_url: Mapped[str | None] = mapped_column(String(500))
    author_texts_video_url: Mapped[str | None] = mapped_column(String(500))
    unique_token_count: Mapped[int | None] = mapped_column(Integer)
    text_length: Mapped[int | None] = mapped_column(Integer)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("author_texts_users.author_texts_user_id", ondelete="RESTRICT"), nullable=False
    )

    creator: Mapped[AuthorTextsUser] = relationship(back_populates="texts")
    likes: Mapped[list["AuthorTextsLike"]] = relationship(back_populates="text")


class AuthorTextsLike(AuthorTextsBase):
    __tablename__ = "author_texts_text_likes"
    __table_args__ = (
        UniqueConstraint(
            "researcher_id", "author_text_id", name="uq_author_texts_researcher_text_like"
        ),
    )

    author_texts_like_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    researcher_id: Mapped[int] = mapped_column(
        ForeignKey("author_texts_users.author_texts_user_id", ondelete="RESTRICT"), nullable=False
    )
    author_text_id: Mapped[int] = mapped_column(
        ForeignKey("author_texts.author_text_id", ondelete="RESTRICT"), nullable=False
    )

    researcher: Mapped[AuthorTextsUser] = relationship(back_populates="likes")
    text: Mapped[AuthorText] = relationship(back_populates="likes")
