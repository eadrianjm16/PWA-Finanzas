"""Añade logo a bank_connections (URL del logo del banco que da Enable
Banking, para mostrarlo en Saldo en vez de solo el nombre). Columna
nullable, no toca datos existentes — las conexiones ya vinculadas se
rellenan solas la próxima vez que se reautoricen.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-13
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "bank_connections", "logo"):
        op.add_column("bank_connections", sa.Column("logo", sa.String(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
