from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _seed_transactions(user_id: str) -> None:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key="Search Bank", aspsp_name="Search Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-search-{user_id}", user_id=user_id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    db.add(
        models.Transaction(
            entry_reference=f"search-mercadona-{user_id}",
            account_uid=account.account_uid,
            amount=45.0,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=datetime.now(timezone.utc),
            remittance_information="COMPRA MERCADONA MADRID",
        )
    )
    db.add(
        models.Transaction(
            entry_reference=f"search-netflix-{user_id}",
            account_uid=account.account_uid,
            amount=12.99,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=datetime.now(timezone.utc),
            remittance_information="",
            counterparty_name="Netflix",
        )
    )
    db.commit()
    db.close()


def test_search_matches_remittance_information():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transactions(me["id"])

        response = client.get("/api/transactions?search=mercadona", headers=auth_headers(token))

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert "MERCADONA" in results[0]["remittance_information"]


def test_search_matches_counterparty_name_case_insensitively():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transactions(me["id"])

        response = client.get("/api/transactions?search=netflix", headers=auth_headers(token))

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["counterparty_name"] == "Netflix"


def test_search_with_no_matches_returns_empty():
    with TestClient(app) as client:
        _, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_transactions(me["id"])

        response = client.get("/api/transactions?search=inexistente", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json() == []
