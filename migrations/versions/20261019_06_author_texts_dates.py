"""Restore the system creation and publication timestamps required by the course."""
import sqlalchemy as sa
from alembic import op

revision = "20261019_06"
down_revision = "20261018_05"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("author_texts", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("author_texts", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    # Historic dates cannot be reconstructed. Keep old published_at NULL.


def downgrade():
    op.drop_column("author_texts", "published_at")
    op.drop_column("author_texts", "created_at")
