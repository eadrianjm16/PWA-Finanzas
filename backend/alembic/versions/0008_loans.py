"""Tabla nueva loans (seguimiento manual de préstamos/créditos externos,
p. ej. Cofidis/Cetelem, actualizados a mano cada extracto). No toca datos
existentes.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "loans"):
        op.create_table(
            "loans",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("credit_limit", sa.Numeric(18, 2), nullable=True),
            sa.Column("balance", sa.Numeric(18, 2), nullable=False),
            sa.Column("monthly_payment", sa.Numeric(18, 2), nullable=False),
            sa.Column("tin", sa.Numeric(6, 2), nullable=True),
            sa.Column("tae", sa.Numeric(6, 2), nullable=True),
            sa.Column("next_payment_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
