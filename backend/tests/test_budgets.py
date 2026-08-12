from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _first_category_id(client, token) -> str:
    categories = client.get("/api/categories", headers=auth_headers(token)).json()
    return categories[0]["id"]


def _seed_previous_month_spend(user_id: str, category_id: str, amount: float) -> str:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key="Budget Bank", aspsp_name="Budget Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account_uid = f"acc-budget-{user_id}"
    account = models.LinkedAccount(
        account_uid=account_uid, user_id=user_id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    last_month = datetime.now(timezone.utc).replace(day=1) - timedelta(days=15)
    db.add(
        models.Transaction(
            entry_reference=f"prevmonth-{user_id}",
            account_uid=account_uid,
            category_id=category_id,
            amount=amount,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=last_month,
            remittance_information="Gasto mes pasado",
        )
    )
    db.commit()
    db.close()
    return account_uid


def test_budget_without_rollover_ignores_previous_month_leftover():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        category_id = _first_category_id(client, token)
        _seed_previous_month_spend(me["id"], category_id, 30.0)  # gasto 30 de un limite de 100 -> sobran 70

        response = client.put(
            f"/api/budgets/{category_id}", json={"monthly_limit": 100, "rollover": False}, headers=auth_headers(token)
        )

    assert response.status_code == 200
    body = response.json()
    assert body["monthly_limit"] == 100
    assert body["effective_limit"] == 100
    assert body["rollover"] is False


def test_budget_with_rollover_adds_previous_month_leftover():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        category_id = _first_category_id(client, token)
        _seed_previous_month_spend(me["id"], category_id, 30.0)  # sobraron 70 de 100

        response = client.put(
            f"/api/budgets/{category_id}", json={"monthly_limit": 100, "rollover": True}, headers=auth_headers(token)
        )

    assert response.status_code == 200
    body = response.json()
    assert body["effective_limit"] == 170  # 100 + (100 - 30)


def test_budget_with_rollover_never_subtracts_when_overspent_last_month():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        category_id = _first_category_id(client, token)
        _seed_previous_month_spend(me["id"], category_id, 150.0)  # se paso del limite de 100

        response = client.put(
            f"/api/budgets/{category_id}", json={"monthly_limit": 100, "rollover": True}, headers=auth_headers(token)
        )

    assert response.json()["effective_limit"] == 100  # nunca resta, como mucho suma 0


def test_list_budgets_reflects_rollover():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        category_id = _first_category_id(client, token)
        _seed_previous_month_spend(me["id"], category_id, 20.0)
        client.put(f"/api/budgets/{category_id}", json={"monthly_limit": 50, "rollover": True}, headers=auth_headers(token))

        listed = client.get("/api/budgets", headers=auth_headers(token)).json()

    by_category = {b["category"]["id"]: b for b in listed}
    assert by_category[category_id]["effective_limit"] == 80  # 50 + (50 - 20)
