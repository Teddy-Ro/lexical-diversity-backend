"""Use an S3-compatible bucket name: underscores are not allowed in buckets."""

import sqlalchemy as sa
from alembic import op

revision = "20261004_04"
down_revision = "20261004_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("author_texts_image_url", "author_texts_video_url"):
        op.execute(sa.text(
            f"UPDATE author_texts SET {column} = replace({column}, '/author_texts-media/', '/author-texts-media/') "
            f"WHERE {column} LIKE 'http://localhost:9000/author_texts-media/%'"
        ))


def downgrade() -> None:
    pass  # Restoring invalid media URLs would only break existing cards.
