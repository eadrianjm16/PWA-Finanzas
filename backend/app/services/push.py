"""Envio de notificaciones Web Push (popups del sistema operativo/navegador)
para alertas nuevas. Sin VAPID_PRIVATE_KEY configurada, no falla nada - solo
no llega a enviar (igual que email.py con Resend)."""

import json
import logging
from datetime import date, datetime, time, timedelta, timezone

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


def _iso_week_key(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def maybe_send_weekly_digest(db: Session, user_id: str) -> None:
    """Manda como mucho un push por semana ISO con el gasto de la semana y la
    categoria con mas gasto. Sin cron en el plan gratuito, se comprueba en
    cada sync (igual que notify_new_alerts) - por eso solo se envia desde el
    viernes en adelante, para que se sienta como un resumen de "la semana" y
    no un aviso a mitad de semana con datos a medias."""
    if not settings.vapid_private_key:
        return

    today = date.today()
    if today.weekday() < 4:  # antes del viernes
        return

    subscriptions = db.query(models.PushSubscription).filter_by(user_id=user_id).all()
    if not subscriptions:
        return

    week_key = _iso_week_key(today)
    if db.get(models.WeeklyDigestLog, (user_id, week_key)) is not None:
        return

    week_start = today - timedelta(days=today.weekday())
    week_start_dt = datetime.combine(week_start, time.min, tzinfo=timezone.utc)

    rows = (
        db.query(models.Transaction, models.Category)
        .join(models.LinkedAccount)
        .outerjoin(models.Category, models.Transaction.category_id == models.Category.id)
        .filter(models.LinkedAccount.user_id == user_id)
        .filter(models.LinkedAccount.is_visible.is_(True))
        .filter(models.Transaction.credit_debit_indicator == "DBIT")
        .filter(models.Transaction.booking_date >= week_start_dt)
        .all()
    )
    if not rows:
        return

    total = sum(abs(float(tx.amount)) for tx, _ in rows)
    spend_by_category: dict[str, float] = {}
    for tx, category in rows:
        name = category.name if category else "Sin categoría"
        spend_by_category[name] = spend_by_category.get(name, 0) + abs(float(tx.amount))
    top_category = max(spend_by_category, key=spend_by_category.get)

    payload = {
        "title": "Resumen semanal",
        "body": f"Esta semana has gastado {total:.2f}€. Tu categoría con más gasto: {top_category}.",
        "alert_id": f"weekly-{week_key}",
    }
    for subscription in subscriptions:
        if not _send_one(subscription, payload):
            db.delete(subscription)

    db.add(models.WeeklyDigestLog(user_id=user_id, week_key=week_key))
    db.commit()
