from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def test_create_check_and_uncheck_resets_next_month():
    with TestClient(app) as client:
        _, token = register_user(client)

        create = client.post(
            "/api/fixed-expenses",
            json={"name": "Alquiler", "amount": 800, "due_day": 5},
            headers=auth_headers(token),
        )
        assert create.status_code == 201
        expense_id = create.json()["id"]
        assert create.json()["checked"] is False

        checked = client.post(f"/api/fixed-expenses/{expense_id}/check?month=2026-08", headers=auth_headers(token))
        assert checked.json()["checked"] is True

        this_month = client.get("/api/fixed-expenses?month=2026-08", headers=auth_headers(token)).json()
        assert this_month[0]["checked"] is True

        next_month = client.get("/api/fixed-expenses?month=2026-09", headers=auth_headers(token)).json()
        assert next_month[0]["checked"] is False  # se resetea solo, sin fila = sin marcar


def test_uncheck_removes_the_mark():
    with TestClient(app) as client:
        _, token = register_user(client)
        expense_id = client.post(
            "/api/fixed-expenses", json={"name": "Gimnasio", "amount": 30, "due_day": 1}, headers=auth_headers(token)
        ).json()["id"]

        client.post(f"/api/fixed-expenses/{expense_id}/check?month=2026-08", headers=auth_headers(token))
        response = client.delete(f"/api/fixed-expenses/{expense_id}/check?month=2026-08", headers=auth_headers(token))

    assert response.json()["checked"] is False


def test_delete_fixed_expense():
    with TestClient(app) as client:
        _, token = register_user(client)
        expense_id = client.post(
            "/api/fixed-expenses", json={"name": "Seguro", "amount": 40, "due_day": 10}, headers=auth_headers(token)
        ).json()["id"]

        delete = client.delete(f"/api/fixed-expenses/{expense_id}", headers=auth_headers(token))
        assert delete.status_code == 204
        assert client.get("/api/fixed-expenses", headers=auth_headers(token)).json() == []


def test_summary_without_income_detected_or_manual():
    with TestClient(app) as client:
        _, token = register_user(client)
        client.post("/api/fixed-expenses", json={"name": "Luz", "amount": 60, "due_day": 15}, headers=auth_headers(token))

        summary = client.get("/api/fixed-expenses/summary", headers=auth_headers(token)).json()

    assert summary["total_fixed"] == 60
    assert summary["estimated_income"] is None
    assert summary["estimated_leftover"] is None
    assert summary["income_is_manual"] is False


def test_summary_uses_manual_income_override():
    with TestClient(app) as client:
        _, token = register_user(client)
        client.post("/api/fixed-expenses", json={"name": "Luz", "amount": 60, "due_day": 15}, headers=auth_headers(token))
        client.put("/api/fixed-expenses/income-override", json={"monthly_amount": 2000}, headers=auth_headers(token))

        summary = client.get("/api/fixed-expenses/summary", headers=auth_headers(token)).json()

    assert summary["estimated_income"] == 2000
    assert summary["income_is_manual"] is True
    assert summary["estimated_leftover"] == 1940


def test_summary_detects_recurring_income_when_no_override():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        client.post("/api/fixed-expenses", json={"name": "Luz", "amount": 60, "due_day": 15}, headers=auth_headers(token))

        db = SessionLocal()
        connection = models.BankConnection(user_id=me["id"], key="Payroll Bank", aspsp_name="Payroll Bank", aspsp_country="ES")
        db.add(connection)
        db.flush()
        account = models.LinkedAccount(
            account_uid=f"acc-payroll-{me['id']}", user_id=me["id"], connection_id=connection.id, display_name="Cuenta"
        )
        db.add(account)
        db.flush()
        category = db.query(models.Category).filter_by(user_id=me["id"], name="Nómina/Ingresos").first()
        for days_ago in [62, 31, 1]:
            db.add(
                models.Transaction(
                    entry_reference=f"payroll-{days_ago}-{me['id']}",
                    account_uid=account.account_uid,
                    category_id=category.id,
                    amount=1800.0,
                    currency="EUR",
                    credit_debit_indicator="CRDT",
                    booking_date=datetime.now(timezone.utc) - timedelta(days=days_ago),
                    remittance_information="NOMINA EMPRESA SL",
                )
            )
        db.commit()
        db.close()

        summary = client.get("/api/fixed-expenses/summary", headers=auth_headers(token)).json()

    assert summary["estimated_income"] == 1800
    assert summary["income_is_manual"] is False
    assert summary["estimated_leftover"] == 1740
