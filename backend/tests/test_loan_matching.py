import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, engine
from app.loan_matching import find_matching_payment


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
    user = models.User(email=f"loanmatch-{uuid.uuid4()}@example.com", password_hash="x")
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


def _tx(account_uid: str, amount: float, remittance: str, days_ago: int = 1, counterparty: str | None = None):
    return models.Transaction(
        entry_reference=f"tx-{uuid.uuid4()}",
        account_uid=account_uid,
        amount=amount,
        currency="EUR",
        credit_debit_indicator="DBIT",
        booking_date=datetime.now(timezone.utc) - timedelta(days=days_ago),
        remittance_information=remittance,
        counterparty_name=counterparty,
    )


def test_matches_a_transaction_by_lender_name_and_similar_amount(db, account):
    loan = models.Loan(
        user_id=account.user_id, name="Cofidis - Crédito Directo", balance=1000, monthly_payment=198.73
    )
    db.add(loan)
    db.add(_tx(account.account_uid, -198.73, "RECIBO COFIDIS PRESTAMO"))
    db.commit()

    match = find_matching_payment(db, account.user_id, loan)

    assert match is not None
    assert "COFIDIS" in match.remittance_information


def test_amount_tolerance_allows_small_variance(db, account):
    loan = models.Loan(user_id=account.user_id, name="Cetelem", balance=1500, monthly_payment=53.04)
    db.add(loan)
    db.add(_tx(account.account_uid, -53.10, "ADEUDO CETELEM"))
    db.commit()

    assert find_matching_payment(db, account.user_id, loan) is not None


def test_does_not_match_when_amount_is_too_different(db, account):
    loan = models.Loan(user_id=account.user_id, name="Cetelem", balance=1500, monthly_payment=53.04)
    db.add(loan)
    db.add(_tx(account.account_uid, -90.00, "ADEUDO CETELEM"))
    db.commit()

    assert find_matching_payment(db, account.user_id, loan) is None


def test_does_not_match_unrelated_transaction_with_same_amount(db, account):
    loan = models.Loan(user_id=account.user_id, name="Cetelem", balance=1500, monthly_payment=53.04)
    db.add(loan)
    db.add(_tx(account.account_uid, -53.04, "MERCADONA MADRID"))
    db.commit()

    assert find_matching_payment(db, account.user_id, loan) is None


def test_ignores_transactions_before_the_search_window(db, account):
    loan = models.Loan(
        user_id=account.user_id,
        name="Cofidis",
        balance=1000,
        monthly_payment=198.73,
        next_payment_date=datetime.now(timezone.utc),
    )
    db.add(loan)
    db.add(_tx(account.account_uid, -198.73, "RECIBO COFIDIS", days_ago=60))
    db.commit()

    assert find_matching_payment(db, account.user_id, loan) is None
