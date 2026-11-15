"""Add the attribute dictionary and vertical text attribute values."""
import sqlalchemy as sa
from alembic import op

revision = "20261115_07"
down_revision = "20261019_06"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "author_texts_attributes",
        sa.Column("author_texts_attribute_id", sa.Integer(), primary_key=True),
        sa.Column("attribute_name", sa.String(100), nullable=False),
        sa.CheckConstraint("length(trim(attribute_name)) > 0", name="ck_author_texts_attribute_name"),
        sa.UniqueConstraint("attribute_name"),
    )
    op.create_table(
        "author_texts_attribute_values",
        sa.Column("author_texts_attribute_value_id", sa.Integer(), primary_key=True),
        sa.Column("author_text_id", sa.Integer(), nullable=False),
        sa.Column("author_texts_attribute_id", sa.Integer(), nullable=False),
        sa.Column("attribute_value", sa.String(500), nullable=False),
        sa.ForeignKeyConstraint(["author_text_id"], ["author_texts.author_text_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_texts_attribute_id"], ["author_texts_attributes.author_texts_attribute_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("author_text_id", "author_texts_attribute_id", name="uq_author_texts_text_attribute"),
        sa.CheckConstraint("length(trim(attribute_value)) > 0", name="ck_author_texts_attribute_value"),
    )
    op.create_index("ix_author_texts_attribute_values_attribute", "author_texts_attribute_values", ["author_texts_attribute_id"])


def downgrade():
    op.drop_index("ix_author_texts_attribute_values_attribute", "author_texts_attribute_values")
    op.drop_table("author_texts_attribute_values")
    op.drop_table("author_texts_attributes")
