"""Logica de negocio para vincular cuentas bancarias y sincronizar movimientos.

Puerto de AccountsStore.swift + TransactionsStore.swift. Igual que en la app
iOS: idempotente (reautorizar una cuenta ya vinculada actualiza la fila, no
duplica; sincronizar dos veces no duplica movimientos) y nunca pisa una
categoria que el usuario ya asigno a mano.
"""

import hashlib
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import insert
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..categorization import suggest_category
from .enable_banking import EnableBankingClient, EnableBankingError, pick_available_balance

BACKFILL_WINDOW = timedelta(days=90)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def link_accounts(db: Session, session_data: dict, aspsp: dict, user_id: str) -> models.BankConnection:
    accounts = session_data.get("accounts") or []
    if not accounts:
        raise EnableBankingError(422, "No se encontraron cuentas tras autorizar el acceso.")

    aspsp_name = aspsp["name"].strip()
    aspsp_country = aspsp["country"].strip()
    connection_key = f"{aspsp_name}|{aspsp_country}"

    connection = db.query(models.BankConnection).filter_by(user_id=user_id, key=connection_key).first()
    if connection is None:
        connection = models.BankConnection(
            user_id=user_id, aspsp_name=aspsp_name, aspsp_country=aspsp_country, key=connection_key
        )
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
                    user_id=user_id,
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


def _category_for(db: Session, user_id: str, name: str) -> models.Category | None:
    return db.query(models.Category).filter_by(user_id=user_id, name=name).first()


def _categories_by_name(db: Session, user_id: str) -> dict[str, models.Category]:
    return {c.name: c for c in db.query(models.Category).filter_by(user_id=user_id).all()}


def _matching_rule_category_id(rules: list[models.CategorizationRule], text: str) -> str | None:
    upper = text.upper()
    for rule in rules:
        if rule.keyword.upper() in upper:
            return rule.category_id
    return None


def _amount_key(value) -> str:
    return f"{float(value):.2f}"


def _pending_by_content(db: Session, account_uid: str) -> dict[tuple, models.Transaction]:
    """Movimientos aun pendientes (PDNG) de esta cuenta, indexados por su
    contenido. El banco asigna una referencia provisional a un pago pendiente
    y otra distinta cuando se liquida (BOOK) - sin esto, sync_transactions no
    tiene forma de saber que son el mismo movimiento y lo duplicaria."""
    rows = db.query(models.Transaction).filter_by(account_uid=account_uid, status="PDNG").all()
    return {
        (_amount_key(row.amount), row.currency, row.remittance_information, row.credit_debit_indicator): row
        for row in rows
    }


INSERT_CHUNK_SIZE = 200


async def sync_transactions(db: Session, account: models.LinkedAccount, client: EnableBankingClient) -> None:
    """Trae movimientos nuevos desde el ultimo sync (o desde 90 dias atras la
    primera vez) y los inserta de forma idempotente.

    Categorias y duplicados se resuelven contra datos precargados en memoria
    en vez de una consulta por movimiento, y las filas nuevas se insertan con
    `insert(...).values(lista)` (un unico statement con N VALUES) en vez de
    un INSERT por fila: con una base de datos remota como Turso, cada
    round-trip de red cuenta - con ~250 movimientos en un primer backfill,
    la version anterior (una consulta y un INSERT por movimiento) tardaba
    30+ segundos; esta version tarda bajo un segundo.
    """
    date_from = account.last_synced_at.date() if account.last_synced_at else (date.today() - BACKFILL_WINDOW)
    raw_transactions = await client.fetch_all_transactions(account.account_uid, date_from=date_from, date_to=date.today())

    categories = _categories_by_name(db, account.user_id)
    rules = db.query(models.CategorizationRule).filter_by(user_id=account.user_id).all()
    existing_keys = {
        row[0]
        for row in db.query(models.Transaction.entry_reference)
        .filter_by(account_uid=account.account_uid)
        .all()
    }
    pending_by_content = _pending_by_content(db, account.account_uid)

    new_rows: list[dict] = []
    for eb_tx in raw_transactions:
        key = eb_tx.get("entry_reference") or _fallback_key(eb_tx)
        if key in existing_keys:
            continue
        existing_keys.add(key)

        indicator = eb_tx["credit_debit_indicator"]
        amount = eb_tx["transaction_amount"]["amount"]
        currency = eb_tx["transaction_amount"]["currency"]
        remittance = "\n".join(eb_tx.get("remittance_information") or [])
        status = eb_tx.get("status")
        counterparty = (eb_tx.get("debtor") if indicator == "CRDT" else eb_tx.get("creditor")) or {}
        mcc = eb_tx.get("merchant_category_code")

        if status != "PDNG":
            stale = pending_by_content.pop((_amount_key(amount), currency, remittance, indicator), None)
            if stale is not None:
                db.query(models.DebtEntry).filter_by(transaction_entry_reference=stale.entry_reference).update(
                    {"transaction_entry_reference": None}
                )
                db.delete(stale)

        rule_category_id = _matching_rule_category_id(rules, remittance or counterparty.get("name") or "")
        if rule_category_id:
            category = next((c for c in categories.values() if c.id == rule_category_id), None)
        else:
            category_name = suggest_category(mcc=mcc, remittance_information=remittance, credit_debit_indicator=indicator)
            category = categories.get(category_name)

        new_rows.append(
            dict(
                entry_reference=key,
                account_uid=account.account_uid,
                category_id=category.id if category else None,
                amount=amount,
                currency=currency,
                credit_debit_indicator=indicator,
                booking_date=_parse_date(eb_tx.get("booking_date")) or datetime.now(timezone.utc),
                value_date=_parse_date(eb_tx.get("value_date")),
                remittance_information=remittance,
                counterparty_name=counterparty.get("name"),
                merchant_category_code=mcc,
                status=status,
            )
        )

    for i in range(0, len(new_rows), INSERT_CHUNK_SIZE):
        chunk = new_rows[i : i + INSERT_CHUNK_SIZE]
        db.execute(insert(models.Transaction).values(chunk))

    account.last_synced_at = datetime.now(timezone.utc)
    db.commit()


def delete_connection(db: Session, connection: models.BankConnection) -> None:
    db.delete(connection)
    db.commit()


def recategorize_uncategorized(db: Session, user_id: str) -> int:
    """Vuelve a pasar el motor de categorizacion sobre movimientos que nunca
    se categorizaron a mano. Util tras ampliar las reglas de categorizacion."""
    pending = (
        db.query(models.Transaction)
        .join(models.LinkedAccount)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.Transaction.is_user_categorized.is_(False))
        .options(joinedload(models.Transaction.category))
        .all()
    )
    categories = _categories_by_name(db, user_id)
    rules = db.query(models.CategorizationRule).filter_by(user_id=user_id).all()
    updated = 0
    for tx in pending:
        rule_category_id = _matching_rule_category_id(
            rules, tx.remittance_information or tx.counterparty_name or ""
        )
        if rule_category_id:
            new_category_id = rule_category_id
        else:
            name = suggest_category(
                mcc=tx.merchant_category_code,
                remittance_information=tx.remittance_information,
                credit_debit_indicator=tx.credit_debit_indicator,
            )
            category = categories.get(name)
            new_category_id = category.id if category else None

        if new_category_id is None or (tx.category is not None and tx.category.id == new_category_id):
            continue
        tx.category_id = new_category_id
        updated += 1
    db.commit()
    return updated
