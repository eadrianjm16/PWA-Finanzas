from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key", response_model=schemas.VapidPublicKeyOut)
def vapid_public_key() -> schemas.VapidPublicKeyOut:
    return schemas.VapidPublicKeyOut(public_key=settings.vapid_public_key, enabled=bool(settings.vapid_private_key))


@router.post("/subscribe", response_model=schemas.MessageResponse)
def subscribe(
    payload: schemas.PushSubscribeRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.MessageResponse:
    existing = db.query(models.PushSubscription).filter_by(endpoint=payload.endpoint).first()
    if existing is not None:
        existing.user_id = user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
    else:
        db.add(
            models.PushSubscription(
                user_id=user.id, endpoint=payload.endpoint, p256dh=payload.keys.p256dh, auth=payload.keys.auth
            )
        )
    db.commit()
    return schemas.MessageResponse(message="Suscripción guardada")


@router.post("/unsubscribe", response_model=schemas.MessageResponse)
def unsubscribe(
    payload: schemas.PushUnsubscribeRequest,
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> schemas.MessageResponse:
    db.query(models.PushSubscription).filter_by(endpoint=payload.endpoint, user_id=user.id).delete()
    db.commit()
    return schemas.MessageResponse(message="Suscripción eliminada")
