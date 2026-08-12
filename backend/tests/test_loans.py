from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers, register_user


def _create_loan(client: TestClient, token: str, **overrides) -> dict:
    payload = {
        "name": "Cofidis - Crédito Directo",
        "credit_limit": 2000.0,
        "balance": 1823.35,
        "monthly_payment": 198.73,
        "tin": 21.79,
        "tae": None,
    }
    payload.update(overrides)
    response = client.post("/api/loans", json=payload, headers=auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_loan():
    with TestClient(app) as client:
        _, token = register_user(client)
        created = _create_loan(client, token)

        response = client.get("/api/loans", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == created["id"]
    assert body[0]["balance"] == 1823.35
    assert body[0]["tin"] == 21.79
    assert body[0]["tae"] is None


def test_cannot_create_loan_with_negative_balance():
    with TestClient(app) as client:
        _, token = register_user(client)
        response = client.post(
            "/api/loans",
            json={"name": "Test", "balance": -10, "monthly_payment": 50},
            headers=auth_headers(token),
        )
    assert response.status_code == 422


def test_update_loan_refreshes_balance_after_new_statement():
    with TestClient(app) as client:
        _, token = register_user(client)
        loan = _create_loan(client, token)

        response = client.patch(
            f"/api/loans/{loan['id']}",
            json={"balance": 1515.24, "monthly_payment": 53.04, "tin": 14.95, "tae": 16.02},
            headers=auth_headers(token),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 1515.24
    assert body["monthly_payment"] == 53.04
    assert body["tin"] == 14.95
    assert body["tae"] == 16.02
    # Campos no incluidos en el PATCH no deberian cambiar.
    assert body["name"] == "Cofidis - Crédito Directo"
    assert body["credit_limit"] == 2000.0


def test_update_loan_rejects_negative_monthly_payment():
    with TestClient(app) as client:
        _, token = register_user(client)
        loan = _create_loan(client, token)

        response = client.patch(
            f"/api/loans/{loan['id']}", json={"monthly_payment": -5}, headers=auth_headers(token)
        )
    assert response.status_code == 422


def test_delete_loan():
    with TestClient(app) as client:
        _, token = register_user(client)
        loan = _create_loan(client, token)

        delete = client.delete(f"/api/loans/{loan['id']}", headers=auth_headers(token))
        listing = client.get("/api/loans", headers=auth_headers(token))

    assert delete.status_code == 204
    assert listing.json() == []


def test_cannot_access_another_users_loan():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        loan = _create_loan(client, token_a)

        _, token_b = register_user(client)
        response = client.patch(
            f"/api/loans/{loan['id']}", json={"balance": 1}, headers=auth_headers(token_b)
        )
    assert response.status_code == 404
