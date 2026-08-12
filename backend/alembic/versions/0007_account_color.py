"""Añade color a linked_accounts (identifica visualmente cada cuenta y sus
movimientos). Columna NOT NULL con default constante vía ALTER TABLE ADD
COLUMN (soportado en SQLite/libsql, a diferencia de un FK inline - ver
0006); las cuentas existentes se recolorean después según el nombre real
de su banco, duplicando aquí la misma tabla de colores conocidos que usa
app/bank_colors.py (sin importar código de la app: mismo criterio que 0001,
controlar exactamente el SQL que se ejecuta).

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-12
"""

import hashlib

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_DEFAULT_COLOR = "#6366F1"

_FALLBACK_PALETTE = [
    "#6366F1", "#F97316", "#10B981", "#EC4899", "#0EA5E9",
    "#F59E0B", "#8B5CF6", "#14B8A6", "#EF4444", "#84CC16",
]

_KNOWN_BANK_COLORS = [
    ("santander", "#EC0000"),
    ("bbva", "#004481"),
    ("caixabank", "#00AEEF"),
    ("la caixa", "#00AEEF"),
    ("sabadell", "#0099CC"),
    ("bankinter", "#FF6600"),
    ("ing", "#FF6200"),
    ("openbank", "#00AEEF"),
    ("unicaja", "#00953B"),
    ("kutxabank", "#E2001A"),
    ("abanca", "#0066B3"),
    ("ibercaja", "#003DA5"),
    ("evo banco", "#C6007E"),
    ("revolut", "#0666EB"),
    ("n26", "#36A18B"),
    ("wise", "#9FE870"),
    ("cofidis", "#E2001A"),
    ("cetelem", "#00A950"),
    ("bnp paribas", "#00915A"),
    ("deutsche bank", "#0018A8"),
    ("triodos", "#00A19A"),
    ("pibank", "#7B2FF7"),
    ("myinvestor", "#001489"),
    ("imagin", "#FF4D6D"),
]


def _resolve_color(aspsp_name: str, seed: str) -> str:
    name = (aspsp_name or "").strip().lower()
    for needle, color in _KNOWN_BANK_COLORS:
        if needle in name:
            return color
    index = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(_FALLBACK_PALETTE)
    return _FALLBACK_PALETTE[index]


def _has_column(bind, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "linked_accounts", "color"):
        op.add_column(
            "linked_accounts",
            sa.Column("color", sa.String(), nullable=False, server_default=_DEFAULT_COLOR),
        )

    rows = bind.execute(
        sa.text(
            """
            SELECT la.account_uid, bc.aspsp_name
            FROM linked_accounts la
            JOIN bank_connections bc ON bc.id = la.connection_id
            WHERE la.color = :default_color
            """
        ),
        {"default_color": _DEFAULT_COLOR},
    ).fetchall()

    for account_uid, aspsp_name in rows:
        bind.execute(
            sa.text("UPDATE linked_accounts SET color = :color WHERE account_uid = :uid"),
            {"color": _resolve_color(aspsp_name, account_uid), "uid": account_uid},
        )


def downgrade() -> None:
    raise NotImplementedError("Sin downgrade automatico para esta migracion.")
