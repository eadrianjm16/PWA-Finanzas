from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_PASSWORD


def test_login_with_correct_password_returns_token():
    with TestClient(app) as client:
        response = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_is_rejected():
    with TestClient(app) as client:
        response = client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


def test_protected_endpoint_requires_auth():
    with TestClient(app) as client:
        response = client.get("/api/accounts")
    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_token():
    with TestClient(app) as client:
        login_response = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
        token = login_response.json()["access_token"]
        response = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_login_is_rate_limited_after_repeated_attempts():
    with TestClient(app) as client:
        statuses = [client.post("/api/auth/login", json={"password": "wrong"}).status_code for _ in range(6)]
    assert 429 in statuses
