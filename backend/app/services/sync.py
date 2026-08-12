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
from ..bank_colors import resolve_account_color
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
                    color=resolve_account_color(aspsp_name, account_uid),
                )
            )

    db.commit()
    db.refresh(connection)
    return connection


def describe_enable_banking_error(error: EnableBankingError) -> str:
    if error.status == 401:
        return "El banco pidió reautorizar el acceso — vuelve a conectarlo"
    if error.status == 429:
        # Muchos bancos (regulacion PSD2/Berlin Group) limitan las llamadas de
        # solo-consulta a un puñado al dia por cuenta fuera de una sesion con
        # el usuario presente - no es necesariamente cuestion de minutos,
        # puede tardar horas o hasta el dia siguiente en resetearse. Si el
        # banco manda cuanto hay que esperar (Retry-After), se lo decimos tal
        # cual en vez de adivinar "unos minutos".
        if error.retry_after_seconds:
            minutes = max(1, error.retry_after_seconds // 60)
            return f"El banco está limitando las peticiones — inténtalo de nuevo en {minutes} min"
        return "El banco está limitando las peticiones — algunos bancos solo dejan sincronizar unas pocas veces al día, prueba más tarde"
    if error.status >= 500:
        return "El banco no está respondiendo ahora mismo — inténtalo más tarde"
    return "No se pudo sincronizar con el banco"


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
        account.last_sync_issue = describe_enable_banking_error(error)
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


def learn_rule_from_categorization(db: Session, user_id: str, keyword: str | None, category_id: str) -> None:
    """Cuando el usuario categoriza un movimiento a mano, se recuerda para la
    proxima vez: crea (o actualiza si ya existia) una regla con el nombre del
    comercio como palabra clave. Solo se usa counterparty_name -no
    remittance_information-, que suele traer sufijos variables (ciudad,
    numero de terminal...) y haria la regla demasiado estrecha o demasiado
    ancha segun el caso."""
    keyword = (keyword or "").strip()
    if not keyword:
        return

    existing = (
        db.query(models.CategorizationRule)
        .filter_by(user_id=user_id)
        .filter(models.CategorizationRule.keyword.ilike(keyword))
        .first()
    )
    if existing is not None:
        existing.category_id = category_id
    else:
        db.add(models.CategorizationRule(user_id=user_id, keyword=keyword, category_id=category_id))


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


async def sync_transactions(db: Session, account: models.LinkedAccount, client: EnableBankingClient) -> list[dict]:
    """Trae movimientos nuevos desde el ultimo sync (o desde 90 dias atras la
    primera vez) y los inserta de forma idempotente.

    Categorias y duplicados se resuelven contra datos precargados en memoria
    en vez de una consulta por movimiento, y las filas nuevas se insertan con
    `insert(...).values(lista)` (un unico statement con N VALUES) en vez de
    un INSERT por fila: con una base de datos remota como Turso, cada
    round-trip de red cuenta - con ~250 movimientos en un primer backfill,
    la version anterior (una consulta y un INSERT por movimiento) tardaba
    30+ segundos; esta version tarda bajo un segundo.

    Devuelve los movimientos nuevos que se categorizaron por una regla
    aprendida (no por la sugerencia automatica) - el router los usa para
    avisar de "N movimientos categorizados automaticamente".
    """
    date_from = account.last_synced_at.date() if account.last_synced_at else (date.today() - BACKFILL_WINDOW)
    try:
        raw_transactions = await client.fetch_all_transactions(
            account.account_uid, date_from=date_from, date_to=date.today()
        )
    except EnableBankingError as error:
        # Antes este error solo se mostraba como un banner generico y
        # desaparecia al navegar; ahora tambien queda guardado en la cuenta
        # (visible en Saldo) con un mensaje que dice que hacer, igual que
        # refresh_balance - el caso mas comun con banco real es que el
        # consentimiento PSD2 caducó (401) y hay que reconectar el banco.
        account.last_sync_issue = describe_enable_banking_error(error)
        db.commit()
        raise

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
    rule_applied: list[dict] = []
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
            if category is not None:
                rule_applied.append(
                    {
                        "name": counterparty.get("name") or remittance.split("\n")[0].strip() or "Movimiento",
                        "category_name": category.name,
                        "amount": float(amount),
                        "currency": currency,
                    }
                )
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
    account.last_sync_issue = None
    db.commit()
    return rule_applied


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


def apply_rules_to_all_matching(db: Session, user_id: str) -> int:
    """A diferencia de recategorize_uncategorized, esta SI puede pisar
    movimientos que el usuario ya categorizo a mano - pero solo cuando una
    regla explicita coincide (nunca por la sugerencia automatica): es una
    accion aparte que el usuario dispara a proposito cuando quiere que sus
    reglas manden sobre todo el historico, no algo que pase por defecto."""
    transactions = (
        db.query(models.Transaction).join(models.LinkedAccount).filter(models.LinkedAccount.user_id == user_id).all()
    )
    rules = db.query(models.CategorizationRule).filter_by(user_id=user_id).all()
    if not rules:
        return 0

    updated = 0
    for tx in transactions:
        rule_category_id = _matching_rule_category_id(rules, tx.remittance_information or tx.counterparty_name or "")
        if rule_category_id is None or tx.category_id == rule_category_id:
            continue
        tx.category_id = rule_category_id
        updated += 1
    db.commit()
    return updated
