from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_PASSWORD, auth_headers, register_user


def test_register_creates_a_user_and_returns_a_token():
    with TestClient(app) as client:
        email, token = register_user(client)
    assert token


def test_register_rejects_a_duplicate_email():
    with TestClient(app) as client:
        email, _ = register_user(client)
        response = client.post("/api/auth/register", json={"email": email, "password": TEST_PASSWORD})
    assert response.status_code == 409


def test_register_rejects_a_short_password():
    with TestClient(app) as client:
        response = client.post("/api/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert response.status_code == 422


def test_register_seeds_default_categories_for_the_new_user():
    with TestClient(app) as client:
        _, token = register_user(client)
        response = client.get("/api/categories", headers=auth_headers(token))
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_login_with_correct_password_returns_token():
    with TestClient(app) as client:
        email, _ = register_user(client)
        response = client.post("/api/auth/login", json={"email": email, "password": TEST_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_is_rejected():
    with TestClient(app) as client:
        email, _ = register_user(client)
        response = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD}
        )
    assert response.status_code == 401


def test_protected_endpoint_requires_auth():
    with TestClient(app) as client:
        response = client.get("/api/accounts")
    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_token():
    with TestClient(app) as client:
        _, token = register_user(client)
        response = client.get("/api/accounts", headers=auth_headers(token))
    assert response.status_code == 200


def test_login_is_rate_limited_after_repeated_attempts():
    with TestClient(app) as client:
        statuses = [
            client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}).status_code
            for _ in range(6)
        ]
    assert 429 in statuses
