import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, engine
from app.services.enable_banking import EnableBankingError
from app.services.sync import learn_rule_from_categorization, link_accounts, sync_transactions


@pytest.fixture
def db():
    models.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def account(db: Session) -> models.LinkedAccount:
    user = models.User(email=f"sync-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    connection = models.BankConnection(user_id=user.id, key="Test Bank|ES", aspsp_name="Test Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-{uuid.uuid4()}", user_id=user.id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    db.add(models.Category(user_id=user.id, name="Alimentación", system_icon_name="shopping-cart", sort_order=0))
    db.add(models.Category(user_id=user.id, name="Otros", system_icon_name="help-circle", sort_order=1))
    db.commit()
    return account


class FakeClient:
    def __init__(self, transactions: list[dict]):
        self._transactions = transactions

    async def fetch_all_transactions(self, account_uid, date_from=None, date_to=None):
        return self._transactions


def _eb_tx(
    entry_reference: str, amount: str = "-20.00", remittance: str = "MERCADONA MADRID", status: str = "BOOK"
) -> dict:
    return {
        "entry_reference": entry_reference,
        "credit_debit_indicator": "DBIT",
        "transaction_amount": {"amount": amount, "currency": "EUR"},
        "booking_date": "2026-03-05",
        "remittance_information": [remittance],
        "merchant_category_code": None,
        "status": status,
    }


async def test_sync_inserts_and_categorizes_new_transactions(db, account):
    client = FakeClient([_eb_tx("tx-1"), _eb_tx("tx-2", remittance="ALGO RARO SIN REGLA")])

    await sync_transactions(db, account, client)

    transactions = db.query(models.Transaction).filter_by(account_uid=account.account_uid).all()
    assert len(transactions) == 2
    by_ref = {tx.entry_reference: tx for tx in transactions}
    assert by_ref["tx-1"].category.name == "Alimentación"
    assert by_ref["tx-2"].category.name == "Otros"
    assert account.last_synced_at is not None


async def test_sync_is_idempotent_and_does_not_duplicate(db, account):
    client = FakeClient([_eb_tx("tx-dup")])

    await sync_transactions(db, account, client)
    await sync_transactions(db, account, client)

    count = db.query(models.Transaction).filter_by(account_uid=account.account_uid, entry_reference="tx-dup").count()
    assert count == 1


async def test_sync_replaces_pending_transaction_once_booked(db, account):
    # El banco da una referencia provisional mientras el pago esta pendiente
    # (PDNG) y otra distinta cuando se liquida (BOOK): mismo movimiento real,
    # dos entry_reference. No deberia quedar como dos filas.
    pending = _eb_tx("prov-123", amount="-33.29", remittance="COMPRA BlaBlaCar, Paris", status="PDNG")
    booked = _eb_tx("final-456", amount="-33.29", remittance="COMPRA BlaBlaCar, Paris", status="BOOK")

    await sync_transactions(db, account, FakeClient([pending]))
    await sync_transactions(db, account, FakeClient([pending, booked]))

    rows = (
        db.query(models.Transaction)
        .filter_by(account_uid=account.account_uid, remittance_information="COMPRA BlaBlaCar, Paris")
        .all()
    )
    assert len(rows) == 1
    assert rows[0].entry_reference == "final-456"
    assert rows[0].status == "BOOK"


async def test_categorization_rule_overrides_automatic_suggestion(db, account):
    # Sin regla, "BAR PACO" cae en Otros (no hay keyword automatica). Con una
    # regla del usuario ("PACO" -> Alimentacion), debe ganarle a esa sugerencia.
    rule_category = db.query(models.Category).filter_by(user_id=account.user_id, name="Alimentación").first()
    db.add(models.CategorizationRule(user_id=account.user_id, keyword="PACO", category_id=rule_category.id))
    db.commit()

    client = FakeClient([_eb_tx("tx-rule", remittance="BAR PACO MADRID")])
    await sync_transactions(db, account, client)

    tx = db.query(models.Transaction).filter_by(entry_reference="tx-rule").first()
    assert tx.category.name == "Alimentación"


async def test_sync_reports_which_transactions_a_rule_categorized(db, account):
    rule_category = db.query(models.Category).filter_by(user_id=account.user_id, name="Alimentación").first()
    db.add(models.CategorizationRule(user_id=account.user_id, keyword="ALGO RARO", category_id=rule_category.id))
    db.commit()

    client = FakeClient([_eb_tx("tx-reported", remittance="ALGO RARO SIN REGLA")])
    applied = await sync_transactions(db, account, client)

    assert len(applied) == 1
    assert applied[0]["category_name"] == "Alimentación"


async def test_learn_rule_from_categorization_creates_then_updates(db, account):
    alimentacion = db.query(models.Category).filter_by(user_id=account.user_id, name="Alimentación").first()
    otros = db.query(models.Category).filter_by(user_id=account.user_id, name="Otros").first()

    learn_rule_from_categorization(db, account.user_id, "Netflix", alimentacion.id)
    db.commit()
    rules = db.query(models.CategorizationRule).filter_by(user_id=account.user_id, keyword="Netflix").all()
    assert len(rules) == 1
    assert rules[0].category_id == alimentacion.id

    # Categorizar el mismo comercio otra vez con otra categoria actualiza la
    # regla existente en vez de crear una duplicada.
    learn_rule_from_categorization(db, account.user_id, "Netflix", otros.id)
    db.commit()
    rules = db.query(models.CategorizationRule).filter_by(user_id=account.user_id, keyword="Netflix").all()
    assert len(rules) == 1
    assert rules[0].category_id == otros.id


async def test_sync_deduplicates_within_the_same_batch(db, account):
    # Dos movimientos identicos en la misma respuesta (raro, pero posible si
    # el fallback key coincide): no deberia intentar insertar dos filas con
    # la misma primary key.
    client = FakeClient([_eb_tx("tx-batch-dup"), _eb_tx("tx-batch-dup")])

    await sync_transactions(db, account, client)

    count = db.query(models.Transaction).filter_by(entry_reference="tx-batch-dup").count()
    assert count == 1


class FailingClient:
    def __init__(self, status: int):
        self._status = status

    async def fetch_all_transactions(self, account_uid, date_from=None, date_to=None):
        raise EnableBankingError(self._status, "boom")


async def test_sync_transactions_persists_a_friendly_reauth_message_on_401(db, account):
    with pytest.raises(EnableBankingError):
        await sync_transactions(db, account, FailingClient(401))

    assert account.last_sync_issue == "El banco pidió reautorizar el acceso — vuelve a conectarlo"


async def test_sync_transactions_clears_the_stale_issue_after_a_successful_sync(db, account):
    account.last_sync_issue = "El banco pidió reautorizar el acceso — vuelve a conectarlo"
    db.commit()

    await sync_transactions(db, account, FakeClient([_eb_tx("tx-recovered")]))

    assert account.last_sync_issue is None


def test_link_accounts_assigns_a_color_based_on_the_real_bank(db):
    user = models.User(email=f"linkcolor-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.commit()

    session_data = {
        "accounts": [{"uid": "acc-bbva-1", "name": "Cuenta Corriente", "account_id": {"iban": "ES1234"}}]
    }
    link_accounts(db, session_data, {"name": "BBVA", "country": "ES"}, user.id)

    account = db.get(models.LinkedAccount, "acc-bbva-1")
    assert account.color == "#004481"


def test_link_accounts_stores_the_bank_logo(db):
    user = models.User(email=f"linklogo-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.commit()

    session_data = {"accounts": [{"uid": "acc-logo-1", "name": "Cuenta", "account_id": {}}]}
    connection = link_accounts(
        db, session_data, {"name": "BBVA", "country": "ES", "logo": "https://cdn.example/bbva.png"}, user.id
    )

    assert connection.logo == "https://cdn.example/bbva.png"


def test_link_accounts_without_a_logo_leaves_it_empty(db):
    user = models.User(email=f"linknologo-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.commit()

    session_data = {"accounts": [{"uid": "acc-nologo-1", "name": "Cuenta", "account_id": {}}]}
    connection = link_accounts(db, session_data, {"name": "Banco Sin Logo", "country": "ES"}, user.id)

    assert connection.logo is None


def test_reauthorizing_backfills_a_missing_logo(db):
    user = models.User(email=f"backfilllogo-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.commit()

    session_data = {"accounts": [{"uid": "acc-backfill-1", "name": "Cuenta", "account_id": {}}]}
    link_accounts(db, session_data, {"name": "Banco Viejo", "country": "ES"}, user.id)
    connection = link_accounts(
        db, session_data, {"name": "Banco Viejo", "country": "ES", "logo": "https://cdn.example/nuevo.png"}, user.id
    )

    assert connection.logo == "https://cdn.example/nuevo.png"
