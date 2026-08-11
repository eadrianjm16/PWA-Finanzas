"""Añade soporte multiusuario: tabla users + user_id en bank_connections,
linked_accounts, categories y debtors. Migra todos los datos existentes al
usuario original (preserva su contraseña actual via APP_PASSWORD_HASH).

Se reescribe cada tabla a mano con SQL explicito (CREATE + INSERT...SELECT +
DROP + RENAME) en vez de usar el modo batch automatico de Alembic: sobre una
base de datos con datos financieros reales, preferimos controlar exactamente
que SQL se ejecuta antes que confiar en la reconstruccion automatica.

Cada paso comprueba si ya se aplico antes de ejecutarse: en un entorno como
Render, un fallo a mitad (p. ej. una variable de entorno que falta) puede
hacer que la plataforma reintente el arranque desde cero, y sin estas
comprobaciones el segundo intento chocaria con "table already exists" en
vez de continuar donde se quedo.

Revision ID: 0001
Revises:
Create Date: 2026-08-11
"""

import os
import uuid

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    # SQLite/libsql no permite ALTER/DROP de una tabla mientras otra la
    # referencia por FK con la comprobacion activada.
    bind.execute(sa.text("PRAGMA foreign_keys=OFF"))

    # 1. Tabla de usuarios (si un intento anterior ya la creo, no la tocamos).
    if not _table_exists(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    # 2. Usuario original: preserva el email y la contraseña que ya tenias
    # (via APP_PASSWORD_HASH, definida en el entorno de despliegue) para que
    # tu login actual siga funcionando exactamente igual tras la migracion.
    owner_email = os.environ.get("MIGRATION_OWNER_EMAIL", "adrian.jibmac@gmail.com").strip().lower()
    existing_owner = bind.execute(
        sa.text("SELECT id FROM users WHERE email = :email"), {"email": owner_email}
    ).first()

    if existing_owner is not None:
        owner_id = existing_owner[0]
    else:
        existing_hash = os.environ.get("APP_PASSWORD_HASH", "")
        if not existing_hash:
            raise RuntimeError(
                "APP_PASSWORD_HASH no esta definida en el entorno: hace falta para crear "
                "el primer usuario preservando tu contraseña actual."
            )
        owner_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO users (id, email, password_hash, created_at) "
                "VALUES (:id, :email, :hash, CURRENT_TIMESTAMP)"
            ),
            {"id": owner_id, "email": owner_email, "hash": existing_hash},
        )

    # 3. bank_connections: + user_id, unique (key) -> unique (user_id, key).
    if not _has_column(bind, "bank_connections", "user_id"):
        op.execute(
            """
            CREATE TABLE bank_connections_new (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id),
                "key" VARCHAR NOT NULL,
                aspsp_name VARCHAR NOT NULL,
                aspsp_country VARCHAR NOT NULL,
                linked_at DATETIME NOT NULL,
                UNIQUE (user_id, "key")
            )
            """
        )
        bind.execute(
            sa.text(
                "INSERT INTO bank_connections_new (id, user_id, key, aspsp_name, aspsp_country, linked_at) "
                "SELECT id, :uid, key, aspsp_name, aspsp_country, linked_at FROM bank_connections"
            ),
            {"uid": owner_id},
        )
        op.execute("DROP TABLE bank_connections")
        op.execute("ALTER TABLE bank_connections_new RENAME TO bank_connections")

    # 4. linked_accounts: + user_id (denormalizado desde la conexion, para no
    # tener que hacer join extra en cada consulta de movimientos).
    if not _has_column(bind, "linked_accounts", "user_id"):
        op.execute(
            """
            CREATE TABLE linked_accounts_new (
                account_uid VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id),
                connection_id VARCHAR NOT NULL REFERENCES bank_connections(id),
                display_name VARCHAR NOT NULL,
                iban VARCHAR,
                last_synced_at DATETIME,
                last_balance_amount VARCHAR,
                last_balance_currency VARCHAR,
                last_balance_refreshed_at DATETIME,
                linked_at DATETIME NOT NULL,
                is_visible BOOLEAN NOT NULL,
                is_balance_visible BOOLEAN NOT NULL,
                last_sync_issue VARCHAR
            )
            """
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO linked_accounts_new (
                    account_uid, user_id, connection_id, display_name, iban, last_synced_at,
                    last_balance_amount, last_balance_currency, last_balance_refreshed_at,
                    linked_at, is_visible, is_balance_visible, last_sync_issue
                )
                SELECT
                    account_uid, :uid, connection_id, display_name, iban, last_synced_at,
                    last_balance_amount, last_balance_currency, last_balance_refreshed_at,
                    linked_at, is_visible, is_balance_visible, last_sync_issue
                FROM linked_accounts
                """
            ),
            {"uid": owner_id},
        )
        op.execute("DROP TABLE linked_accounts")
        op.execute("ALTER TABLE linked_accounts_new RENAME TO linked_accounts")

    # 5. categories: + user_id, unique (name) -> unique (user_id, name).
    if not _has_column(bind, "categories", "user_id"):
        op.execute(
            """
            CREATE TABLE categories_new (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id),
                name VARCHAR NOT NULL,
                system_icon_name VARCHAR NOT NULL,
                sort_order INTEGER NOT NULL,
                UNIQUE (user_id, name)
            )
            """
        )
        bind.execute(
            sa.text(
                "INSERT INTO categories_new (id, user_id, name, system_icon_name, sort_order) "
                "SELECT id, :uid, name, system_icon_name, sort_order FROM categories"
            ),
            {"uid": owner_id},
        )
        op.execute("DROP TABLE categories")
        op.execute("ALTER TABLE categories_new RENAME TO categories")

    # 6. debtors: + user_id, unique (name) -> unique (user_id, name).
    if not _has_column(bind, "debtors", "user_id"):
        op.execute(
            """
            CREATE TABLE debtors_new (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id),
                name VARCHAR NOT NULL,
                created_at DATETIME NOT NULL,
                UNIQUE (user_id, name)
            )
            """
        )
        bind.execute(
            sa.text(
                "INSERT INTO debtors_new (id, user_id, name, created_at) "
                "SELECT id, :uid, name, created_at FROM debtors"
            ),
            {"uid": owner_id},
        )
        op.execute("DROP TABLE debtors")
        op.execute("ALTER TABLE debtors_new RENAME TO debtors")

    # transactions, budgets y debt_entries no cambian de columnas: su scope de
    # usuario es transitivo (via linked_accounts / categories / debtors), y
    # sus FK siguen apuntando a las tablas recien recreadas por nombre.

    integrity_errors = list(bind.execute(sa.text("PRAGMA foreign_key_check")))
    if integrity_errors:
        raise RuntimeError(f"Migracion abortada: foreign_key_check encontro problemas: {integrity_errors}")

    bind.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    raise NotImplementedError(
        "Sin downgrade automatico: revertir esto significa perder el aislamiento "
        "por usuario. Restaura desde un backup/branch de Turso si hace falta volver atras."
    )
