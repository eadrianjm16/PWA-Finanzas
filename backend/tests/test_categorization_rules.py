from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers, register_user


def _first_category_id(client, token) -> str:
    categories = client.get("/api/categories", headers=auth_headers(token)).json()
    return categories[0]["id"]


def test_create_list_and_delete_rule():
    with TestClient(app) as client:
        _, token = register_user(client)
        category_id = _first_category_id(client, token)

        create = client.post(
            "/api/categorization-rules",
            json={"keyword": "PACO", "category_id": category_id},
            headers=auth_headers(token),
        )
        assert create.status_code == 201
        rule_id = create.json()["id"]

        listed = client.get("/api/categorization-rules", headers=auth_headers(token)).json()
        assert len(listed) == 1
        assert listed[0]["keyword"] == "PACO"

        delete = client.delete(f"/api/categorization-rules/{rule_id}", headers=auth_headers(token))
        assert delete.status_code == 204
        assert client.get("/api/categorization-rules", headers=auth_headers(token)).json() == []


def test_cannot_create_rule_with_another_users_category():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        _, token_b = register_user(client)
        category_id = _first_category_id(client, token_a)

        response = client.post(
            "/api/categorization-rules",
            json={"keyword": "X", "category_id": category_id},
            headers=auth_headers(token_b),
        )
    assert response.status_code == 404
