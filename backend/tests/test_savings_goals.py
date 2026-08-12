from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers, register_user


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
