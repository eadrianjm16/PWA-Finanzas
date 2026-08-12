from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from tests.conftest import auth_headers, register_user


def _seed_bank_fee(email: str) -> None:
    db = SessionLocal()
    user = db.query(models.User).filter_by(email=email).first()
    connection = models.BankConnection(user_id=user.id, key="Test Bank|ES", aspsp_name="Test Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-fee-{user.id}", user_id=user.id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    category = db.query(models.Category).filter_by(user_id=user.id, name="Comisiones bancarias").first()
    db.add(
        models.Transaction(
            entry_reference=f"fee-tx-{user.id}",
            account_uid=account.account_uid,
            category_id=category.id,
            amount=4.5,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=datetime.now(timezone.utc),
            remittance_information="Comision mantenimiento",
        )
    )
    db.commit()
    db.close()


def test_bank_fee_alert_appears_after_seeding_a_fee_transaction():
    with TestClient(app) as client:
        email, token = register_user(client)
        before = client.get("/api/alerts", headers=auth_headers(token)).json()
        _seed_bank_fee(email)
        after = client.get("/api/alerts", headers=auth_headers(token)).json()

    assert before == []
    assert len(after) == 1
    assert after[0]["icon"] == "bank-fee"


def test_dismissing_an_alert_removes_it_and_persists():
    with TestClient(app) as client:
        email, token = register_user(client)
        _seed_bank_fee(email)
        alerts = client.get("/api/alerts", headers=auth_headers(token)).json()
        alert_id = alerts[0]["id"]

        dismiss_response = client.delete(f"/api/alerts/{alert_id}", headers=auth_headers(token))
        after_dismiss = client.get("/api/alerts", headers=auth_headers(token)).json()

    assert dismiss_response.status_code == 200
    assert after_dismiss == []


def test_dismissing_an_alert_twice_does_not_error():
    with TestClient(app) as client:
        email, token = register_user(client)
        _seed_bank_fee(email)
        alerts = client.get("/api/alerts", headers=auth_headers(token)).json()
        alert_id = alerts[0]["id"]

        first = client.delete(f"/api/alerts/{alert_id}", headers=auth_headers(token))
        second = client.delete(f"/api/alerts/{alert_id}", headers=auth_headers(token))

    assert first.status_code == 200
    assert second.status_code == 200


def test_dismissing_an_alert_does_not_affect_other_users():
    with TestClient(app) as client:
        email_a, token_a = register_user(client)
        _, token_b = register_user(client)
        _seed_bank_fee(email_a)
        alerts_a = client.get("/api/alerts", headers=auth_headers(token_a)).json()
        alert_id = alerts_a[0]["id"]

        client.delete(f"/api/alerts/{alert_id}", headers=auth_headers(token_b))
        after_a = client.get("/api/alerts", headers=auth_headers(token_a)).json()

    assert len(after_a) == 1
