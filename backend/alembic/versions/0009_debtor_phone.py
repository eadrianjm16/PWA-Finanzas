"""Añade phone a debtors (opcional, para poder notificarles un reparto por
WhatsApp). Columna nullable, no toca datos existentes.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "debtors", "phone"):
        op.add_column("debtors", sa.Column("phone", sa.String(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
