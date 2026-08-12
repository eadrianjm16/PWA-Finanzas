from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _seed_account(user_id: str, aspsp_name: str = "Test Bank") -> str:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key=f"{aspsp_name}|ES", aspsp_name=aspsp_name, aspsp_country="ES")
    db.add(connection)
    db.flush()
    account_uid = f"acc-{user_id}"
    db.add(
        models.LinkedAccount(
            account_uid=account_uid,
            user_id=user_id,
            connection_id=connection.id,
            display_name="Cuenta",
            color="#111111",
        )
    )
    db.commit()
    db.close()
    return account_uid


def test_list_accounts_includes_color():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_account(me["id"])

        response = client.get("/api/accounts", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()[0]["color"] == "#111111"


def test_can_update_account_color():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        account_uid = _seed_account(me["id"])

        response = client.patch(
            f"/api/accounts/{account_uid}", json={"color": "#00FF00"}, headers=auth_headers(token)
        )

    assert response.status_code == 200
    assert response.json()["color"] == "#00FF00"


def test_rejects_invalid_color_format():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        account_uid = _seed_account(me["id"])

        response = client.patch(
            f"/api/accounts/{account_uid}", json={"color": "not-a-color"}, headers=auth_headers(token)
        )

    assert response.status_code == 422


def test_transactions_include_account_color():
    from datetime import datetime, timezone

    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        account_uid = _seed_account(me["id"])

        db = SessionLocal()
        db.add(
            models.Transaction(
                entry_reference="tx-color-1",
                account_uid=account_uid,
                amount=-10,
                currency="EUR",
                credit_debit_indicator="DBIT",
                booking_date=datetime.now(timezone.utc),
                remittance_information="Test",
            )
        )
        db.commit()
        db.close()

        response = client.get("/api/transactions", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["account_color"] == "#111111"
