"""Tablas nuevas para descartar alertas y notificaciones Web Push:
alert_dismissals, push_subscriptions, notified_alerts. Ninguna toca datos
existentes, asi que basta con crear cada tabla si no existe ya.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "alert_dismissals"):
        op.create_table(
            "alert_dismissals",
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("alert_id", sa.String(), primary_key=True),
            sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(bind, "push_subscriptions"):
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("endpoint", sa.String(), nullable=False, unique=True),
            sa.Column("p256dh", sa.String(), nullable=False),
            sa.Column("auth", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(bind, "notified_alerts"):
        op.create_table(
            "notified_alerts",
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("alert_id", sa.String(), primary_key=True),
            sa.Column("notified_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
