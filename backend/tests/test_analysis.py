import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app import models
from app.analysis import build_summary
from app.database import SessionLocal, engine


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
def user_id(db: Session) -> str:
    user = models.User(email=f"analysis-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(user)
    db.commit()
    return user.id


def _make_account(db: Session, user_id: str, uid: str, visible: bool = True) -> models.LinkedAccount:
    connection = models.BankConnection(user_id=user_id, key=f"conn-{uid}", aspsp_name="Test Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=uid, user_id=user_id, connection_id=connection.id, display_name=uid, is_visible=visible
    )
    db.add(account)
    db.flush()
    return account


def _make_tx(db, account_uid, entry_reference, amount, indicator, year, month, day, category_id=None):
    db.add(
        models.Transaction(
            entry_reference=entry_reference,
            account_uid=account_uid,
            category_id=category_id,
            amount=amount,
            currency="EUR",
            credit_debit_indicator=indicator,
            booking_date=datetime(year, month, day, tzinfo=timezone.utc),
            remittance_information="",
        )
    )


def test_build_summary_totals_and_six_months(db, user_id):
    account = _make_account(db, user_id, "acc-summary-1")
    category = models.Category(user_id=user_id, name="Test Cat Summary", system_icon_name="tag", sort_order=0)
    db.add(category)
    db.flush()

    _make_tx(db, account.account_uid, "tx-income-1", 1000, "CRDT", 2026, 3, 5)
    _make_tx(db, account.account_uid, "tx-expense-1", 200, "DBIT", 2026, 3, 10, category_id=category.id)
    _make_tx(db, account.account_uid, "tx-prev-1", 300, "DBIT", 2026, 2, 15)
    db.commit()

    summary = build_summary(db, user_id, 2026, 3)

    assert summary["month"] == "2026-03"
    assert summary["income"] == 1000.0
    assert summary["expense"] == 200.0
    assert summary["net"] == 800.0
    assert summary["no_computable"] == 0.0
    assert len(summary["last_six_months"]) == 6
    assert summary["last_six_months"][-1] == {"month": "2026-03", "income": 1000.0, "expense": 200.0, "net": 800.0}
    assert summary["last_six_months"][-2]["month"] == "2026-02"
    assert summary["last_six_months"][-2]["expense"] == 300.0
    assert summary["category_breakdown"][0]["spent"] == 200.0


def test_build_summary_excludes_hidden_accounts(db, user_id):
    # Mes distinto al resto de tests de este archivo: los tests comparten el
    # mismo fichero sqlite de prueba y no estan aislados entre si.
    account = _make_account(db, user_id, "acc-summary-hidden", visible=False)
    _make_tx(db, account.account_uid, "tx-hidden-1", 500, "DBIT", 2031, 7, 1)
    db.commit()

    summary = build_summary(db, user_id, 2031, 7)
    assert summary["expense"] == 0.0


def test_build_summary_excludes_other_users_transactions(db, user_id):
    other_user = models.User(email=f"other-{uuid.uuid4()}@example.com", password_hash="x")
    db.add(other_user)
    db.flush()

    _make_account(db, user_id, "acc-mine-2033")
    other_account = _make_account(db, other_user.id, "acc-other-2033")
    _make_tx(db, other_account.account_uid, "tx-other-1", 999, "DBIT", 2033, 1, 1)
    db.commit()

    summary = build_summary(db, user_id, 2033, 1)
    assert summary["expense"] == 0.0
