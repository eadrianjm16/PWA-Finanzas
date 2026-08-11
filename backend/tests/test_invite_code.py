import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def invite_code_required():
    settings.registration_invite_code = "let-me-in"
    yield "let-me-in"
    settings.registration_invite_code = ""


def test_register_is_open_when_no_invite_code_configured():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            json={"email": f"open-{uuid.uuid4()}@example.com", "password": "password1234"},
        )
    assert response.status_code == 201


def test_register_requires_the_invite_code_when_configured(invite_code_required):
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            json={"email": f"blocked-{uuid.uuid4()}@example.com", "password": "password1234"},
        )
    assert response.status_code == 403


def test_register_rejects_a_wrong_invite_code(invite_code_required):
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": f"wrong-{uuid.uuid4()}@example.com",
                "password": "password1234",
                "invite_code": "not-the-right-code",
            },
        )
    assert response.status_code == 403


def test_register_succeeds_with_the_correct_invite_code(invite_code_required):
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": f"right-{uuid.uuid4()}@example.com",
                "password": "password1234",
                "invite_code": invite_code_required,
            },
        )
    assert response.status_code == 201
