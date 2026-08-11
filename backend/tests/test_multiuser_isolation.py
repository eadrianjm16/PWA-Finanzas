from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers, register_user


def test_debtors_are_isolated_per_user():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        _, token_b = register_user(client)

        client.post("/api/debtors", json={"name": "Juan"}, headers=auth_headers(token_a))

        debtors_a = client.get("/api/debtors", headers=auth_headers(token_a)).json()
        debtors_b = client.get("/api/debtors", headers=auth_headers(token_b)).json()

    assert len(debtors_a) == 1
    assert debtors_a[0]["name"] == "Juan"
    assert debtors_b == []


def test_user_cannot_fetch_another_users_debtor_by_id():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        _, token_b = register_user(client)

        created = client.post("/api/debtors", json={"name": "Ana"}, headers=auth_headers(token_a)).json()

        response = client.get(f"/api/debtors/{created['id']}", headers=auth_headers(token_b))

    assert response.status_code == 404


def test_user_cannot_delete_another_users_debtor():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        _, token_b = register_user(client)

        created = client.post("/api/debtors", json={"name": "Luis"}, headers=auth_headers(token_a)).json()

        delete_response = client.delete(f"/api/debtors/{created['id']}", headers=auth_headers(token_b))
        still_there = client.get("/api/debtors", headers=auth_headers(token_a)).json()

    assert delete_response.status_code == 404
    assert len(still_there) == 1


def test_categories_are_isolated_and_independently_seeded_per_user():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        _, token_b = register_user(client)

        categories_a = client.get("/api/categories", headers=auth_headers(token_a)).json()
        categories_b = client.get("/api/categories", headers=auth_headers(token_b)).json()

    ids_a = {c["id"] for c in categories_a}
    ids_b = {c["id"] for c in categories_b}
    assert len(categories_a) == len(categories_b) > 0
    assert ids_a.isdisjoint(ids_b)


def test_same_category_name_allowed_across_different_users():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        _, token_b = register_user(client)

        response_a = client.post(
            "/api/categories", json={"name": "Mascotas", "system_icon_name": "paw-print"}, headers=auth_headers(token_a)
        )
        response_b = client.post(
            "/api/categories", json={"name": "Mascotas", "system_icon_name": "paw-print"}, headers=auth_headers(token_b)
        )

    assert response_a.status_code == 201
    assert response_b.status_code == 201
