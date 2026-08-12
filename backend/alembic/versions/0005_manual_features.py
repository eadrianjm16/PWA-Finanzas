"""Tablas y columna nuevas para: reglas de categorizacion, metas de ahorro,
presupuestos con remanente, resumen semanal, y Gasto Fijo (+ deteccion de
nomina). Ninguna toca datos existentes salvo la columna `rollover` en
`budgets`, que se anade con default false.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "budgets", "rollover"):
        op.add_column("budgets", sa.Column("rollover", sa.Boolean(), nullable=False, server_default=sa.false()))

    if not _table_exists(bind, "categorization_rules"):
        op.create_table(
            "categorization_rules",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("keyword", sa.String(), nullable=False),
            sa.Column("category_id", sa.String(), sa.ForeignKey("categories.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(bind, "savings_goals"):
        op.create_table(
            "savings_goals",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("current_amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(bind, "weekly_digest_log"):
        op.create_table(
            "weekly_digest_log",
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("week_key", sa.String(), primary_key=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(bind, "fixed_expenses"):
        op.create_table(
            "fixed_expenses",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("due_day", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(bind, "fixed_expense_checks"):
        op.create_table(
            "fixed_expense_checks",
            sa.Column("fixed_expense_id", sa.String(), sa.ForeignKey("fixed_expenses.id"), primary_key=True),
            sa.Column("month_key", sa.String(), primary_key=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(bind, "income_overrides"):
        op.create_table(
            "income_overrides",
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("monthly_amount", sa.Numeric(18, 2), nullable=False),
        )


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
