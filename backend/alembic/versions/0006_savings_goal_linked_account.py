"""Añade linked_account_uid a savings_goals (vincular una meta de ahorro a
una cuenta real, cuyo saldo pasa a ser el progreso). Columna nullable, no
toca datos existentes.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "savings_goals", "linked_account_uid"):
        # Sin sa.ForeignKey() inline: SQLite/libsql no soporta ALTER TABLE ADD
        # COLUMN con constraint fuera de modo batch (ver ddl/sqlite.py de
        # Alembic). El FK ya se declara a nivel de ORM en models.py.
        op.add_column(
            "savings_goals",
            sa.Column("linked_account_uid", sa.String(), nullable=True),
        )


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
