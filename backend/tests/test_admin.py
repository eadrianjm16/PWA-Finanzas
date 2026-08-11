from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _make_admin(email: str) -> None:
    db = SessionLocal()
    user = db.query(models.User).filter_by(email=email).first()
    user.is_admin = True
    db.commit()
    db.close()


def test_me_reflects_admin_flag():
    with TestClient(app) as client:
        email, token = register_user(client)
        before = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _make_admin(email)
        after = client.get("/api/auth/me", headers=auth_headers(token)).json()

    assert before["is_admin"] is False
    assert after["is_admin"] is True


def test_non_admin_cannot_list_users():
    with TestClient(app) as client:
        _, token = register_user(client)
        response = client.get("/api/admin/users", headers=auth_headers(token))
    assert response.status_code == 403


def test_admin_can_list_all_users_with_stats():
    with TestClient(app) as client:
        admin_email, admin_token = register_user(client)
        _make_admin(admin_email)
        _, other_token = register_user(client)
        client.post("/api/debtors", json={"name": "Juan"}, headers=auth_headers(other_token))

        response = client.get("/api/admin/users", headers=auth_headers(admin_token))

    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2
    emails = {u["email"] for u in users}
    assert admin_email in emails
    by_email = {u["email"]: u for u in users}
    assert by_email[admin_email]["debtors_count"] == 0


def test_admin_cannot_delete_own_account_via_admin_endpoint():
    with TestClient(app) as client:
        admin_email, admin_token = register_user(client)
        _make_admin(admin_email)
        me = client.get("/api/auth/me", headers=auth_headers(admin_token)).json()

        response = client.delete(f"/api/admin/users/{me['id']}", headers=auth_headers(admin_token))
    assert response.status_code == 400


def test_admin_can_delete_another_users_account_and_all_their_data():
    with TestClient(app) as client:
        admin_email, admin_token = register_user(client)
        _make_admin(admin_email)
        other_email, other_token = register_user(client)

        other_me = client.get("/api/auth/me", headers=auth_headers(other_token)).json()
        client.post("/api/debtors", json={"name": "Ana"}, headers=auth_headers(other_token))

        delete_response = client.delete(f"/api/admin/users/{other_me['id']}", headers=auth_headers(admin_token))
        relogin = client.post("/api/auth/login", json={"email": other_email, "password": "test-password-123"})

    assert delete_response.status_code == 204
    assert relogin.status_code == 401


def test_non_admin_cannot_delete_a_user():
    with TestClient(app) as client:
        _, token_a = register_user(client)
        _, token_b = register_user(client)
        me_b = client.get("/api/auth/me", headers=auth_headers(token_b)).json()

        response = client.delete(f"/api/admin/users/{me_b['id']}", headers=auth_headers(token_a))
    assert response.status_code == 403
