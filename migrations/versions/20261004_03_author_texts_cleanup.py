"""Remove unused timestamps and finish renaming database sequences."""

import sqlalchemy as sa
from alembic import op

revision = "20261004_03"
down_revision = "20261004_02"
branch_labels = None
depends_on = None

SEQUENCES = {
    "ttr_users_ttr_user_id_seq": "author_texts_users_author_texts_user_id_seq",
    "ttr_texts_ttr_text_id_seq": "author_texts_author_text_id_seq",
    "ttr_text_likes_ttr_like_id_seq": "author_texts_text_likes_author_texts_like_id_seq",
}


def upgrade() -> None:
    for old, new in SEQUENCES.items():
        op.execute(sa.text(f'ALTER SEQUENCE "{old}" RENAME TO "{new}"'))
    op.drop_column("author_texts", "created_at")
    op.drop_column("author_texts", "published_at")


def downgrade() -> None:
    op.add_column("author_texts", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("author_texts", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    for old, new in SEQUENCES.items():
        op.execute(sa.text(f'ALTER SEQUENCE "{new}" RENAME TO "{old}"'))
