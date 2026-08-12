from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _seed_transaction(user_id: str) -> None:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key="Export Bank", aspsp_name="Export Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-export-{user_id}", user_id=user_id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    db.add(
        models.Transaction(
            entry_reference=f"export-tx-{user_id}",
            account_uid=account.account_uid,
            amount=25.5,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=datetime.now(timezone.utc),
            remittance_information="COMPRA TIENDA EXPORT",
        )
    )
    db.commit()
    db.close()


def test_export_returns_csv_with_the_transaction():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transaction(me["id"])

        response = client.get("/api/transactions/export", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "COMPRA TIENDA EXPORT" in body
    assert "25.50" in body
    assert "Gasto" in body


def test_export_respects_search_filter():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transaction(me["id"])

        response = client.get("/api/transactions/export?search=inexistente", headers=auth_headers(token))

    lines = [line for line in response.text.splitlines() if line]
    assert len(lines) == 1  # solo la cabecera
