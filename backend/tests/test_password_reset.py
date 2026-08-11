import jwt
from fastapi.testclient import TestClient

from app.main import app
from app.security import create_password_reset_token
from tests.conftest import register_user


def test_forgot_password_returns_generic_message_for_unknown_email():
    with TestClient(app) as client:
        response = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert "si existe una cuenta" in response.json()["message"].lower()


def test_forgot_password_returns_the_same_generic_message_for_a_real_email():
    with TestClient(app) as client:
        email, _ = register_user(client)
        response = client.post("/api/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    assert "si existe una cuenta" in response.json()["message"].lower()


def test_reset_password_with_a_valid_token_changes_the_password_and_old_password_stops_working():
    with TestClient(app) as client:
        email, _ = register_user(client)

        from app import models
        from app.database import SessionLocal

        db = SessionLocal()
        user = db.query(models.User).filter_by(email=email).first()
        token = create_password_reset_token(user.id, user.password_hash)
        db.close()

        reset_response = client.post(
            "/api/auth/reset-password", json={"token": token, "new_password": "brand-new-password-123"}
        )
        assert reset_response.status_code == 200

        old_login = client.post("/api/auth/login", json={"email": email, "password": "test-password-123"})
        new_login = client.post("/api/auth/login", json={"email": email, "password": "brand-new-password-123"})

    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_reset_password_token_cannot_be_reused_after_password_changed():
    with TestClient(app) as client:
        email, _ = register_user(client)

        from app import models
        from app.database import SessionLocal

        db = SessionLocal()
        user = db.query(models.User).filter_by(email=email).first()
        token = create_password_reset_token(user.id, user.password_hash)
        db.close()

        first = client.post("/api/auth/reset-password", json={"token": token, "new_password": "first-new-password"})
        second = client.post("/api/auth/reset-password", json={"token": token, "new_password": "second-new-password"})

    assert first.status_code == 200
    assert second.status_code == 400


def test_reset_password_rejects_a_garbage_token():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/reset-password", json={"token": "not-a-real-token", "new_password": "whatever12345"}
        )
    assert response.status_code == 400


def test_reset_password_rejects_a_short_password():
    with TestClient(app) as client:
        email, _ = register_user(client)

        from app import models
        from app.database import SessionLocal

        db = SessionLocal()
        user = db.query(models.User).filter_by(email=email).first()
        token = create_password_reset_token(user.id, user.password_hash)
        db.close()

        response = client.post("/api/auth/reset-password", json={"token": token, "new_password": "short"})
    assert response.status_code == 422


def test_reset_password_rejects_a_token_signed_with_the_wrong_secret():
    with TestClient(app) as client:
        email, _ = register_user(client)

        from app import models
        from app.database import SessionLocal

        db = SessionLocal()
        user = db.query(models.User).filter_by(email=email).first()
        db.close()

        forged = jwt.encode(
            {"type": "password_reset", "sub": user.id, "pwfp": "x" * 16},
            "wrong-secret",
            algorithm="HS256",
        )
        response = client.post("/api/auth/reset-password", json={"token": forged, "new_password": "whatever12345"})
    assert response.status_code == 400
