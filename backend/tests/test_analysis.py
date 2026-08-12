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


def test_build_summary_income_breakdown_only_includes_categorized_credits(db, user_id):
    account = _make_account(db, user_id, "acc-income-breakdown")
    payroll = models.Category(user_id=user_id, name="Nómina/Ingresos", system_icon_name="wallet", sort_order=0)
    other_income = models.Category(user_id=user_id, name="Otros ingresos", system_icon_name="tag", sort_order=1)
    expense_category = models.Category(user_id=user_id, name="Ocio", system_icon_name="tag", sort_order=2)
    db.add_all([payroll, other_income, expense_category])
    db.flush()

    _make_tx(db, account.account_uid, "tx-payroll-1", 1800, "CRDT", 2026, 4, 1, category_id=payroll.id)
    _make_tx(db, account.account_uid, "tx-freelance-1", 300, "CRDT", 2026, 4, 5, category_id=other_income.id)
    _make_tx(db, account.account_uid, "tx-uncategorized-income", 50, "CRDT", 2026, 4, 6)
    _make_tx(db, account.account_uid, "tx-leisure-1", 40, "DBIT", 2026, 4, 10, category_id=expense_category.id)
    db.commit()

    summary = build_summary(db, user_id, 2026, 4)

    assert summary["income"] == 2150.0  # 1800 + 300 + 50, incluye el sin categorizar
    by_category_name = {item["category"].name: item["spent"] for item in summary["income_breakdown"]}
    assert by_category_name == {"Nómina/Ingresos": 1800.0, "Otros ingresos": 300.0}
    assert "Ocio" not in by_category_name  # es un gasto, no debe colarse en el desglose de ingresos


def test_budget_used_ratio_only_considers_budgeted_categories(db, user_id):
    # Antes se comparaba el gasto TOTAL del mes contra la suma de los pocos
    # presupuestos fijados, lo que inflaba el % si habia gasto sin presupuestar.
    account = _make_account(db, user_id, "acc-ratio-scope")
    budgeted = models.Category(user_id=user_id, name="Con presupuesto", system_icon_name="tag", sort_order=0)
    unbudgeted = models.Category(user_id=user_id, name="Sin presupuesto", system_icon_name="tag", sort_order=1)
    db.add_all([budgeted, unbudgeted])
    db.flush()
    db.add(models.Budget(category_id=budgeted.id, monthly_limit=100))

    _make_tx(db, account.account_uid, "tx-ratio-budgeted", 80, "DBIT", 2027, 5, 10, category_id=budgeted.id)
    _make_tx(db, account.account_uid, "tx-ratio-unbudgeted", 500, "DBIT", 2027, 5, 11, category_id=unbudgeted.id)
    db.commit()

    summary = build_summary(db, user_id, 2027, 5)

    assert summary["expense"] == 580.0  # el total de gasto del mes sigue sumando todo
    assert summary["budgeted_total"] == 100.0
    assert summary["budget_used_ratio"] == pytest.approx(0.8)  # 80/100, no (80+500)/100


def test_budget_used_ratio_ignores_rollover_for_a_past_month(db, user_id):
    account = _make_account(db, user_id, "acc-ratio-past-rollover")
    category = models.Category(user_id=user_id, name="Rollover pasado", system_icon_name="tag", sort_order=0)
    db.add(category)
    db.flush()
    db.add(models.Budget(category_id=category.id, monthly_limit=100, rollover=True))
    _make_tx(db, account.account_uid, "tx-ratio-past", 50, "DBIT", 2027, 6, 10, category_id=category.id)
    db.commit()

    summary = build_summary(db, user_id, 2027, 6)

    # 2027-06 no es "ahora": el remanente no se recalcula para meses ya
    # cerrados, se usa el limite tal cual.
    assert summary["budgeted_total"] == 100.0
    assert summary["budget_used_ratio"] == pytest.approx(0.5)


def test_budget_used_ratio_applies_rollover_for_the_real_current_month(db, user_id):
    now = datetime.now(timezone.utc)
    this_year, this_month = now.year, now.month
    prev_month = this_month - 1 or 12
    prev_year = this_year if this_month > 1 else this_year - 1

    account = _make_account(db, user_id, "acc-ratio-current-rollover")
    category = models.Category(user_id=user_id, name="Rollover actual", system_icon_name="tag", sort_order=0)
    db.add(category)
    db.flush()
    db.add(models.Budget(category_id=category.id, monthly_limit=100, rollover=True))
    # El mes pasado (real) solo gasto 30 de 100 -> sobran 70 para este mes.
    _make_tx(db, account.account_uid, "tx-ratio-cur-prev", 30, "DBIT", prev_year, prev_month, 5, category_id=category.id)
    _make_tx(db, account.account_uid, "tx-ratio-cur-this", 34, "DBIT", this_year, this_month, 5, category_id=category.id)
    db.commit()

    summary = build_summary(db, user_id, this_year, this_month)

    assert summary["budgeted_total"] == 170.0  # 100 + (100 - 30) de remanente
    assert summary["budget_used_ratio"] == pytest.approx(34 / 170)


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
