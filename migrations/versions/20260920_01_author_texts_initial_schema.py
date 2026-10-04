"""Create the TTR users, texts and likes tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260920_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ttr_users",
        sa.Column("ttr_user_id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("username", name="uq_ttr_users_username"),
    )
    op.create_table(
        "ttr_texts",
        sa.Column("ttr_text_id", sa.Integer(), primary_key=True),
        sa.Column("work_title", sa.String(length=200), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=False),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("short_description", sa.String(length=500), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column(
            "ttr_status",
            sa.Enum(
                "draft",
                "published",
                "deleted",
                name="ttr_text_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("ttr_image_url", sa.String(length=500), nullable=True),
        sa.Column("ttr_video_url", sa.String(length=500), nullable=True),
        sa.Column("unique_token_count", sa.Integer(), nullable=False),
        sa.Column("text_length", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("text_length >= 0", name="ck_ttr_text_length_nonnegative"),
        sa.CheckConstraint(
            "unique_token_count >= 0", name="ck_ttr_unique_token_count_nonnegative"
        ),
        sa.CheckConstraint(
            "publication_year IS NULL OR publication_year BETWEEN 1 AND 2100",
            name="ck_ttr_publication_year",
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"], ["ttr_users.ttr_user_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "uq_ttr_one_draft_per_user",
        "ttr_texts",
        ["creator_id"],
        unique=True,
        postgresql_where=sa.text("ttr_status = 'draft'"),
    )
    op.create_table(
        "ttr_text_likes",
        sa.Column("ttr_like_id", sa.Integer(), primary_key=True),
        sa.Column("researcher_id", sa.Integer(), nullable=False),
        sa.Column("ttr_text_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["researcher_id"], ["ttr_users.ttr_user_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["ttr_text_id"], ["ttr_texts.ttr_text_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "researcher_id", "ttr_text_id", name="uq_ttr_researcher_text_like"
        ),
    )


def downgrade() -> None:
    op.drop_table("ttr_text_likes")
    op.drop_index("uq_ttr_one_draft_per_user", table_name="ttr_texts")
    op.drop_table("ttr_texts")
    op.drop_table("ttr_users")
