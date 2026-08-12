from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers, register_user


def test_create_debtor_with_phone():
    with TestClient(app) as client:
        _, token = register_user(client)
        response = client.post(
            "/api/debtors", json={"name": "Ana", "phone": "+34 612 345 678"}, headers=auth_headers(token)
        )
    assert response.status_code == 201
    assert response.json()["phone"] == "+34 612 345 678"


def test_create_debtor_without_phone_defaults_to_none():
    with TestClient(app) as client:
        _, token = register_user(client)
        response = client.post("/api/debtors", json={"name": "Bruno"}, headers=auth_headers(token))
    assert response.status_code == 201
    assert response.json()["phone"] is None


def test_can_add_phone_to_an_existing_debtor():
    with TestClient(app) as client:
        _, token = register_user(client)
        debtor = client.post("/api/debtors", json={"name": "Carla"}, headers=auth_headers(token)).json()

        response = client.patch(
            f"/api/debtors/{debtor['id']}", json={"phone": "+34600111222"}, headers=auth_headers(token)
        )
    assert response.status_code == 200
    assert response.json()["phone"] == "+34600111222"


def test_can_clear_a_debtors_phone():
    with TestClient(app) as client:
        _, token = register_user(client)
        debtor = client.post(
            "/api/debtors", json={"name": "Dani", "phone": "+34600111222"}, headers=auth_headers(token)
        ).json()

        response = client.patch(f"/api/debtors/{debtor['id']}", json={"phone": None}, headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["phone"] is None


def test_cannot_update_another_users_debtor():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        debtor = client.post("/api/debtors", json={"name": "Eva"}, headers=auth_headers(token_a)).json()

        _, token_b = register_user(client)
        response = client.patch(
            f"/api/debtors/{debtor['id']}", json={"phone": "+34600000000"}, headers=auth_headers(token_b)
        )
    assert response.status_code == 404
