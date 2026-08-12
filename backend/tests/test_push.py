from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import models
from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.services.push import notify_new_alerts
from tests.conftest import auth_headers, register_user


def test_vapid_public_key_reports_disabled_without_private_key():
    with TestClient(app) as client:
        response = client.get("/api/push/vapid-public-key")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_subscribe_and_unsubscribe_persist():
    with TestClient(app) as client:
        _, token = register_user(client)
        subscribe = client.post(
            "/api/push/subscribe",
            json={"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "pkey", "auth": "akey"}},
            headers=auth_headers(token),
        )
        assert subscribe.status_code == 200

        db = SessionLocal()
        count_after_subscribe = db.query(models.PushSubscription).filter_by(endpoint="https://push.example.com/abc").count()
        db.close()
        assert count_after_subscribe == 1

        unsubscribe = client.post(
            "/api/push/unsubscribe", json={"endpoint": "https://push.example.com/abc"}, headers=auth_headers(token)
        )
        assert unsubscribe.status_code == 200

        db = SessionLocal()
        count_after_unsubscribe = db.query(models.PushSubscription).filter_by(endpoint="https://push.example.com/abc").count()
        db.close()
        assert count_after_unsubscribe == 0


def _seed_bank_fee(user_id: str) -> None:
    db = SessionLocal()
    connection = models.BankConnection(user_id=user_id, key="Push Bank|ES", aspsp_name="Push Bank", aspsp_country="ES")
    db.add(connection)
    db.flush()
    account = models.LinkedAccount(
        account_uid=f"acc-push-{user_id}", user_id=user_id, connection_id=connection.id, display_name="Cuenta"
    )
    db.add(account)
    category = db.query(models.Category).filter_by(user_id=user_id, name="Comisiones bancarias").first()
    db.add(
        models.Transaction(
            entry_reference=f"push-fee-{user_id}",
            account_uid=account.account_uid,
            category_id=category.id,
            amount=3.0,
            currency="EUR",
            credit_debit_indicator="DBIT",
            booking_date=datetime.now(timezone.utc),
            remittance_information="Comision push",
        )
    )
    db.commit()
    db.close()


def test_notify_new_alerts_does_nothing_without_vapid_configured():
    with TestClient(app) as client:
        email, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_bank_fee(me["id"])

    assert settings.vapid_private_key == ""
    db = SessionLocal()
    with patch("app.services.push.webpush") as mocked:
        notify_new_alerts(db, me["id"])
    mocked.assert_not_called()
    db.close()


def test_notify_new_alerts_sends_once_and_records_it():
    with TestClient(app) as client:
        email, token = register_user(client)
        me = client.get("/api/auth/me", headers=auth_headers(token)).json()
        _seed_bank_fee(me["id"])

    db = SessionLocal()
    db.add(
        models.PushSubscription(
            user_id=me["id"], endpoint="https://push.example.com/notify-test", p256dh="pkey", auth="akey"
        )
    )
    db.commit()

    with patch.object(settings, "vapid_private_key", "fake-private-key"), patch(
        "app.services.push.webpush"
    ) as mocked:
        notify_new_alerts(db, me["id"])
        assert mocked.call_count == 1
        notify_new_alerts(db, me["id"])  # segunda llamada: la misma alerta no se reenvía
        assert mocked.call_count == 1

    notified = db.query(models.NotifiedAlert).filter_by(user_id=me["id"]).all()
    assert len(notified) == 1
    db.close()
