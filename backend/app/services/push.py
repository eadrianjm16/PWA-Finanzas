"""Envio de notificaciones Web Push (popups del sistema operativo/navegador)
para alertas nuevas. Sin VAPID_PRIVATE_KEY configurada, no falla nada - solo
no llega a enviar (igual que email.py con Resend)."""

import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from .. import models
from ..alerts import evaluate_alerts
from ..config import settings

logger = logging.getLogger("finanzas.push")


def _vapid_claims() -> dict:
    return {"sub": f"mailto:{settings.vapid_admin_email}"}


def _send_one(subscription: models.PushSubscription, payload: dict) -> bool:
    """Devuelve False si la suscripción ya no es válida (el navegador la
    revocó) y debería borrarse."""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims=_vapid_claims(),
        )
        return True
    except WebPushException as error:
        status_code = getattr(error.response, "status_code", None)
        if status_code in (404, 410):
            return False
        logger.error("Error enviando push a %s: %s", subscription.endpoint, error)
        return True


def notify_new_alerts(db: Session, user_id: str) -> None:
    if not settings.vapid_private_key:
        return

    subscriptions = db.query(models.PushSubscription).filter_by(user_id=user_id).all()
    if not subscriptions:
        return

    alerts = evaluate_alerts(db, user_id)
    already_notified = {
        row[0] for row in db.query(models.NotifiedAlert.alert_id).filter_by(user_id=user_id).all()
    }
    new_alerts = [alert for alert in alerts if alert["id"] not in already_notified]
    if not new_alerts:
        return

    for alert in new_alerts:
        payload = {"title": alert["title"], "body": alert["subtitle"], "alert_id": alert["id"]}
        for subscription in subscriptions:
            if not _send_one(subscription, payload):
                db.delete(subscription)
        db.add(models.NotifiedAlert(user_id=user_id, alert_id=alert["id"]))

    db.commit()
