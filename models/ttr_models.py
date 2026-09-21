from datetime import datetime
from enum import StrEnum

from db.ttr_base import TTRBase
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TTRTextStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DELETED = "deleted"


class TTRUser(TTRBase):
    __tablename__ = "ttr_users"

    ttr_user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

    texts: Mapped[list["TTRText"]] = relationship(back_populates="creator")
    likes: Mapped[list["TTRLike"]] = relationship(back_populates="researcher")


class TTRText(TTRBase):
    __tablename__ = "ttr_texts"
    __table_args__ = (
        CheckConstraint("text_length >= 0", name="ck_ttr_text_length_nonnegative"),
        CheckConstraint(
            "unique_token_count >= 0",
            name="ck_ttr_unique_token_count_nonnegative",
        ),
        CheckConstraint(
            "publication_year IS NULL OR publication_year BETWEEN 1 AND 2100",
            name="ck_ttr_publication_year",
        ),
        Index(
            "uq_ttr_one_draft_per_user",
            "creator_id",
            unique=True,
            postgresql_where=text("ttr_status = 'draft'"),
        ),
    )

    ttr_text_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_title: Mapped[str] = mapped_column(String(200), nullable=False)
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    short_description: Mapped[str] = mapped_column(String(500), default="")
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    ttr_status: Mapped[TTRTextStatus] = mapped_column(
        Enum(
            TTRTextStatus,
            name="ttr_text_status",
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=TTRTextStatus.DRAFT,
        nullable=False,
    )
    ttr_image_url: Mapped[str | None] = mapped_column(String(500))
    ttr_video_url: Mapped[str | None] = mapped_column(String(500))
    unique_token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("ttr_users.ttr_user_id", ondelete="RESTRICT"), nullable=False
    )

    creator: Mapped[TTRUser] = relationship(back_populates="texts")
    likes: Mapped[list["TTRLike"]] = relationship(back_populates="text")


class TTRLike(TTRBase):
    __tablename__ = "ttr_text_likes"
    __table_args__ = (
        UniqueConstraint(
            "researcher_id", "ttr_text_id", name="uq_ttr_researcher_text_like"
        ),
    )

    ttr_like_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    researcher_id: Mapped[int] = mapped_column(
        ForeignKey("ttr_users.ttr_user_id", ondelete="RESTRICT"), nullable=False
    )
    ttr_text_id: Mapped[int] = mapped_column(
        ForeignKey("ttr_texts.ttr_text_id", ondelete="RESTRICT"), nullable=False
    )

    researcher: Mapped[TTRUser] = relationship(back_populates="likes")
    text: Mapped[TTRText] = relationship(back_populates="likes")
