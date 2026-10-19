"""Replace source text metadata with manually entered token counts."""

import sqlalchemy as sa
from alembic import op

revision = "20261018_05"
down_revision = "20261004_04"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_author_texts_publication_year", "author_texts", type_="check")
    for column in ("author_name", "publication_year", "text_content"):
        op.drop_column("author_texts", column)
    op.create_check_constraint("ck_author_texts_token_counts", "author_texts", "unique_token_count <= text_length")
    for column, extension in (("author_texts_image_url", "jpg"), ("author_texts_video_url", "webm")):
        op.execute(sa.text(f"UPDATE author_texts SET {column} = :url WHERE {column} IS NULL OR {column} = ''").bindparams(url=f"/author_texts-assets/media/author_texts_default.{extension}"))
        op.alter_column("author_texts", column, existing_type=sa.String(500), nullable=False)


def downgrade():
    for column in ("author_texts_image_url", "author_texts_video_url"):
        op.alter_column("author_texts", column, existing_type=sa.String(500), nullable=True)
    op.drop_constraint("ck_author_texts_token_counts", "author_texts", type_="check")
    op.add_column("author_texts", sa.Column("author_name", sa.String(200), nullable=True))
    op.add_column("author_texts", sa.Column("publication_year", sa.Integer(), nullable=True))
    op.add_column("author_texts", sa.Column("text_content", sa.Text(), nullable=True))
    op.create_check_constraint("ck_author_texts_publication_year", "author_texts", "publication_year IS NULL OR publication_year BETWEEN 1 AND 2100")
