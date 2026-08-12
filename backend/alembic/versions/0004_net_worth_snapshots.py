"""Tabla nueva net_worth_snapshots (historial de patrimonio neto). No toca
datos existentes.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "net_worth_snapshots"):
        op.create_table(
            "net_worth_snapshots",
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("date", sa.String(), primary_key=True),
            sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        )


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
