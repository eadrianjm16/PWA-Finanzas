"""Logica de negocio para vincular cuentas bancarias y sincronizar movimientos.

Puerto de AccountsStore.swift + TransactionsStore.swift. Igual que en la app
iOS: idempotente (reautorizar una cuenta ya vinculada actualiza la fila, no
duplica; sincronizar dos veces no duplica movimientos) y nunca pisa una
categoria que el usuario ya asigno a mano.
"""

import hashlib
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .. import models
from ..categorization import suggest_category
from .enable_banking import EnableBankingClient, EnableBankingError, pick_available_balance

BACKFILL_WINDOW = timedelta(days=90)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def link_accounts(db: Session, session_data: dict, aspsp: dict) -> models.BankConnection:
    accounts = session_data.get("accounts") or []
    if not accounts:
        raise EnableBankingError(422, "No se encontraron cuentas tras autorizar el acceso.")

    aspsp_name = aspsp["name"].strip()
    aspsp_country = aspsp["country"].strip()
    connection_key = f"{aspsp_name}|{aspsp_country}"

    connection = db.query(models.BankConnection).filter_by(key=connection_key).first()
    if connection is None:
        connection = models.BankConnection(aspsp_name=aspsp_name, aspsp_country=aspsp_country, key=connection_key)
        db.add(connection)
        db.flush()

    for account in accounts:
        account_uid = account["uid"]
        iban = (account.get("account_id") or {}).get("iban")
        existing = db.get(models.LinkedAccount, account_uid)
        if existing is not None:
            existing.iban = iban
            existing.connection_id = connection.id
            # Fuerza un backfill completo de movimientos tras reautorizar.
            existing.last_synced_at = None
        else:
            db.add(
                models.LinkedAccount(
                    account_uid=account_uid,
                    display_name=account.get("name") or aspsp_name,
                    iban=iban,
                    connection_id=connection.id,
                )
            )

    db.commit()
    db.refresh(connection)
    return connection


def _balance_error_message(error: EnableBankingError) -> str:
    if error.status == 401:
        return "El banco pidió reautorizar el acceso — vuelve a conectarlo"
    return "No se pudo actualizar el saldo"


async def refresh_balance(db: Session, account: models.LinkedAccount, client: EnableBankingClient) -> None:
    try:
        balances = await client.fetch_balances(account.account_uid)
        balance = pick_available_balance(balances)
        if balance is None:
            return
        account.last_balance_amount = balance["balance_amount"]["amount"]
        account.last_balance_currency = balance["balance_amount"]["currency"]
        account.last_balance_refreshed_at = datetime.now(timezone.utc)
        # last_synced_at es el checkpoint de sync_transactions (marca hasta donde
        # se trajeron movimientos) - no tocarlo aqui o el proximo sync creera
        # que ya sincronizo "ahora mismo" y pedira una ventana vacia.
        account.last_sync_issue = None
        db.commit()
    except EnableBankingError as error:
        account.last_sync_issue = _balance_error_message(error)
        db.commit()
        raise


def _fallback_key(tx: dict) -> str:
    raw = "|".join(
        [
            tx.get("booking_date") or "",
            tx["transaction_amount"]["amount"],
            tx["transaction_amount"]["currency"],
            "".join(tx.get("remittance_information") or []),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _category_for(db: Session, name: str) -> models.Category | None:
    return db.query(models.Category).filter_by(name=name).first()


async def sync_transactions(db: Session, account: models.LinkedAccount, client: EnableBankingClient) -> None:
    """Trae movimientos nuevos desde el ultimo sync (o desde 90 dias atras la
    primera vez) y los inserta de forma idempotente."""
    date_from = account.last_synced_at.date() if account.last_synced_at else (date.today() - BACKFILL_WINDOW)
    raw_transactions = await client.fetch_all_transactions(account.account_uid, date_from=date_from, date_to=date.today())

    for eb_tx in raw_transactions:
        key = eb_tx.get("entry_reference") or _fallback_key(eb_tx)
        if db.get(models.Transaction, key) is not None:
            continue

        indicator = eb_tx["credit_debit_indicator"]
        amount = eb_tx["transaction_amount"]["amount"]
        remittance = "\n".join(eb_tx.get("remittance_information") or [])
        counterparty = (eb_tx.get("debtor") if indicator == "CRDT" else eb_tx.get("creditor")) or {}
        mcc = eb_tx.get("merchant_category_code")

        category_name = suggest_category(mcc=mcc, remittance_information=remittance, credit_debit_indicator=indicator)
        category = _category_for(db, category_name)

        db.add(
            models.Transaction(
                entry_reference=key,
                account_uid=account.account_uid,
                category_id=category.id if category else None,
                amount=amount,
                currency=eb_tx["transaction_amount"]["currency"],
                credit_debit_indicator=indicator,
                booking_date=_parse_date(eb_tx.get("booking_date")) or datetime.now(timezone.utc),
                value_date=_parse_date(eb_tx.get("value_date")),
                remittance_information=remittance,
                counterparty_name=counterparty.get("name"),
                merchant_category_code=mcc,
                status=eb_tx.get("status"),
            )
        )

    account.last_synced_at = datetime.now(timezone.utc)
    db.commit()


def delete_connection(db: Session, connection: models.BankConnection) -> None:
    db.delete(connection)
    db.commit()


def recategorize_uncategorized(db: Session) -> int:
    """Vuelve a pasar el motor de categorizacion sobre movimientos que nunca
    se categorizaron a mano. Util tras ampliar las reglas de categorizacion."""
    pending = db.query(models.Transaction).filter_by(is_user_categorized=False).all()
    updated = 0
    for tx in pending:
        name = suggest_category(
            mcc=tx.merchant_category_code,
            remittance_information=tx.remittance_information,
            credit_debit_indicator=tx.credit_debit_indicator,
        )
        category = _category_for(db, name)
        if category is None or (tx.category is not None and tx.category.name == name):
            continue
        tx.category_id = category.id
        updated += 1
    db.commit()
    return updated
