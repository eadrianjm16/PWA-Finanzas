import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, engine
from app.recurring import detect_recurring_charges


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
    user = models.User(email=f"recurring-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    connection = models.BankConnection(user_id=user.id, key="Test Bank|ES", aspsp_name="Test Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-{uuid.uuid4()}", user_id=user.id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    db.commit()
    return account


def _add_tx(db, account_uid, days_ago, amount, name, entry_reference=None):
    booking_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db.add(
        models.Transaction(
            entry_reference=entry_reference or f"tx-{uuid.uuid4()}",
            account_uid=account_uid,
            amount=amount,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=booking_date,
            remittance_information="",
            counterparty_name=name,
        )
    )


def test_detects_monthly_subscription(db, account):
    _add_tx(db, account.account_uid, 62, 12.99, "Netflix")
    _add_tx(db, account.account_uid, 31, 12.99, "Netflix")
    _add_tx(db, account.account_uid, 1, 12.99, "Netflix")
    db.commit()

    charges = detect_recurring_charges(db, account.user_id)

    assert len(charges) == 1
    assert charges[0]["name"] == "Netflix"
    assert charges[0]["frequency"] == "mensual"
    assert charges[0]["occurrences"] == 3


def test_single_charge_is_not_recurring(db, account):
    _add_tx(db, account.account_uid, 5, 40.0, "IKEA")
    db.commit()

    charges = detect_recurring_charges(db, account.user_id)

    assert charges == []


def test_irregular_gaps_are_not_flagged(db, account):
    _add_tx(db, account.account_uid, 90, 20.0, "Tienda X")
    _add_tx(db, account.account_uid, 45, 20.0, "Tienda X")
    _add_tx(db, account.account_uid, 3, 20.0, "Tienda X")
    db.commit()

    charges = detect_recurring_charges(db, account.user_id)

    assert charges == []


def test_detects_yearly_subscription(db, account):
    _add_tx(db, account.account_uid, 366, 89.0, "Amazon Prime")
    _add_tx(db, account.account_uid, 2, 89.0, "Amazon Prime")
    db.commit()

    charges = detect_recurring_charges(db, account.user_id)

    assert len(charges) == 1
    assert charges[0]["frequency"] == "anual"


def test_other_users_charges_are_not_mixed_in(db, account):
    other_user = models.User(email=f"other-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(other_user)
    db.flush()
    other_connection = models.BankConnection(user_id=other_user.id, key="Other|ES", aspsp_name="Other", aspsp_country="ES")
    db.add(other_connection)
    db.flush()
    other_account = models.LinkedAccount(
        account_uid=f"acc-{uuid.uuid4()}", user_id=other_user.id, connection_id=other_connection.id, display_name="Otra"
    )
    db.add(other_account)
    db.flush()

    _add_tx(db, account.account_uid, 31, 9.99, "Spotify")
    _add_tx(db, account.account_uid, 1, 9.99, "Spotify")
    _add_tx(db, other_account.account_uid, 31, 9.99, "Spotify")
    _add_tx(db, other_account.account_uid, 1, 9.99, "Spotify")
    db.commit()

    charges = detect_recurring_charges(db, account.user_id)

    assert len(charges) == 1
