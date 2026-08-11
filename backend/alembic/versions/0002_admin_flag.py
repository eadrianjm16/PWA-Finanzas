"""Añade is_admin a users y marca como admin al propietario original (el
usuario creado por la migración 0001, identificado por su email).

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12
"""

import os

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "users", "is_admin"):
        op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))

    owner_email = os.environ.get("MIGRATION_OWNER_EMAIL", "adrian.jibmac@gmail.com").strip().lower()
    bind.execute(sa.text("UPDATE users SET is_admin = 1 WHERE email = :email"), {"email": owner_email})


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
