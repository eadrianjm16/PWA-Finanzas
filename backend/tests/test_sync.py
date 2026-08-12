import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, engine
from app.services.sync import sync_transactions


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


async def test_sync_deduplicates_within_the_same_batch(db, account):
    # Dos movimientos identicos en la misma respuesta (raro, pero posible si
    # el fallback key coincide): no deberia intentar insertar dos filas con
    # la misma primary key.
    client = FakeClient([_eb_tx("tx-batch-dup"), _eb_tx("tx-batch-dup")])

    await sync_transactions(db, account, client)

    count = db.query(models.Transaction).filter_by(entry_reference="tx-batch-dup").count()
    assert count == 1
