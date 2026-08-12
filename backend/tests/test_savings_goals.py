from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _seed_account_with_balance(user_id: str, balance: str) -> str:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key="Savings Bank", aspsp_name="Savings Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account_uid = f"acc-savings-{user_id}"
    db.add(
        models.LinkedAccount(
            account_uid=account_uid,
            user_id=user_id,
            connection_id=connection.id,
            display_name="Cuenta Ahorro",
            last_balance_amount=balance,
            last_balance_currency="EUR",
        )
    )
    db.commit()
    db.close()
    return account_uid


def test_create_contribute_and_delete_goal():
    with TestClient(app) as client:
        _, token = register_user(client)

        create = client.post(
            "/api/savings-goals", json={"name": "Viaje", "target_amount": 1000}, headers=auth_headers(token)
        )
        assert create.status_code == 201
        goal = create.json()
        assert goal["current_amount"] == 0

        contribute = client.post(
            f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 250}, headers=auth_headers(token)
        )
        assert contribute.json()["current_amount"] == 250

        withdraw = client.post(
            f"/api/savings-goals/{goal['id']}/contribute", json={"amount": -400}, headers=auth_headers(token)
        )
        assert withdraw.json()["current_amount"] == 0  # no baja de 0

        delete = client.delete(f"/api/savings-goals/{goal['id']}", headers=auth_headers(token))
        assert delete.status_code == 204
        assert client.get("/api/savings-goals", headers=auth_headers(token)).json() == []


def test_cannot_create_goal_with_non_positive_target():
    with TestClient(app) as client:
        _, token = register_user(client)
        response = client.post(
            "/api/savings-goals", json={"name": "Nada", "target_amount": 0}, headers=auth_headers(token)
        )
    assert response.status_code == 422


def test_creating_a_goal_linked_to_an_account_uses_its_balance_as_progress():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        account_uid = _seed_account_with_balance(me["id"], "450.75")

        response = client.post(
            "/api/savings-goals",
            json={"name": "Fondo emergencia", "target_amount": 2000, "linked_account_uid": account_uid},
            headers=auth_headers(token),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["current_amount"] == 450.75
    assert body["linked_account_uid"] == account_uid
    assert body["linked_account_name"] == "Cuenta Ahorro"


def test_linked_goal_rejects_manual_contribution():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        account_uid = _seed_account_with_balance(me["id"], "100.00")
        goal = client.post(
            "/api/savings-goals",
            json={"name": "Meta", "target_amount": 500, "linked_account_uid": account_uid},
            headers=auth_headers(token),
        ).json()

        response = client.post(
            f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 50}, headers=auth_headers(token)
        )
    assert response.status_code == 422


def test_link_and_unlink_goal_after_creation():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        account_uid = _seed_account_with_balance(me["id"], "300.00")
        goal = client.post(
            "/api/savings-goals", json={"name": "Meta", "target_amount": 500}, headers=auth_headers(token)
        ).json()
        assert goal["current_amount"] == 0

        linked = client.put(
            f"/api/savings-goals/{goal['id']}/link", json={"account_uid": account_uid}, headers=auth_headers(token)
        ).json()
        assert linked["current_amount"] == 300.0

        unlinked = client.put(
            f"/api/savings-goals/{goal['id']}/link", json={"account_uid": None}, headers=auth_headers(token)
        ).json()
        assert unlinked["linked_account_uid"] is None
        assert unlinked["current_amount"] == 0  # vuelve al current_amount manual, que nunca se toco


def test_cannot_link_goal_to_another_users_account():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        me_a = client.get("/api/auth/me", headers=auth_headers(token_a)).json()
        account_uid = _seed_account_with_balance(me_a["id"], "100.00")

        _, token_b = register_user(client)
        goal_b = client.post(
            "/api/savings-goals", json={"name": "Meta B", "target_amount": 500}, headers=auth_headers(token_b)
        ).json()

        response = client.put(
            f"/api/savings-goals/{goal_b['id']}/link", json={"account_uid": account_uid}, headers=auth_headers(token_b)
        )
    assert response.status_code == 404
