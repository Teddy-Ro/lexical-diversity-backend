"""Rename the lab domain without replacing existing rows; allow partial drafts."""

import secrets

import sqlalchemy as sa
from alembic import op

revision = "20261004_02"
down_revision = "20260920_01"
branch_labels = None
depends_on = None

TABLES = {
    "ttr_users": "author_texts_users",
    "ttr_texts": "author_texts",
    "ttr_text_likes": "author_texts_text_likes",
}
COLUMNS = {
    "author_texts_users": {"ttr_user_id": "author_texts_user_id"},
    "author_texts": {
        "ttr_text_id": "author_text_id",
        "ttr_status": "author_texts_status",
        "ttr_image_url": "author_texts_image_url",
        "ttr_video_url": "author_texts_video_url",
    },
    "author_texts_text_likes": {
        "ttr_like_id": "author_texts_like_id",
        "ttr_text_id": "author_text_id",
    },
}
OPTIONAL_COLUMNS = {
    "author_name": sa.String(200),
    "short_description": sa.String(500),
    "text_content": sa.Text(),
    "unique_token_count": sa.Integer(),
    "text_length": sa.Integer(),
}


def upgrade() -> None:
    for previous, current in TABLES.items():
        op.rename_table(previous, current)
    for table, columns in COLUMNS.items():
        for previous, current in columns.items():
            op.alter_column(table, previous, new_column_name=current)

    # PostgreSQL keeps constraint names when tables/columns are renamed.
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    for table in TABLES.values():
        constraints = (
            [inspector.get_pk_constraint(table)]
            + inspector.get_foreign_keys(table)
            + inspector.get_unique_constraints(table)
            + inspector.get_check_constraints(table)
        )
        for constraint in constraints:
            old_name = constraint["name"]
            if old_name and "ttr" in old_name:
                new_name = old_name.replace("ttr", "author_texts").replace(
                    "author_texts_texts", "author_texts"
                ).replace("author_texts_text_id", "author_text_id")
                op.execute(sa.text(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'))
    op.execute(sa.text(
        "ALTER INDEX uq_ttr_one_draft_per_user RENAME TO uq_author_texts_one_draft_per_user"
    ))
    for name, column_type in OPTIONAL_COLUMNS.items():
        op.alter_column("author_texts", name, existing_type=column_type, nullable=True)

    op.add_column("author_texts_users", sa.Column("password_hash", sa.String(255), nullable=True))
    # No passwords existed before this migration. Give each old account an
    # independently random password hash; don't introduce a shared known password.
    import hashlib
    for user_id in connection.execute(sa.text("SELECT author_texts_user_id FROM author_texts_users")).scalars().all():
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", secrets.token_bytes(32), salt.encode(), 600_000)
        password_hash = f"pbkdf2_sha256$600000${salt}${digest.hex()}"
        connection.execute(sa.text(
            "UPDATE author_texts_users SET password_hash = :password_hash WHERE author_texts_user_id = :user_id"
        ), {"password_hash": password_hash, "user_id": user_id})
    op.alter_column("author_texts_users", "password_hash", existing_type=sa.String(255), nullable=False)

    # Rewrite only the bundled demo asset paths; preserve custom media URLs.
    for column in ("author_texts_image_url", "author_texts_video_url"):
        connection.execute(sa.text(
            f"UPDATE author_texts SET {column} = replace({column}, '/ttr-media/ttr-', '/author_texts-media/author_texts-') "
            f"WHERE {column} LIKE 'http://localhost:9000/ttr-media/ttr-%'"
        ))


def downgrade() -> None:
    # Refuse to discard partial drafts or password hashes on an automatic rollback.
    raise RuntimeError("Restore the database backup to return to the pre-author_texts schema.")
