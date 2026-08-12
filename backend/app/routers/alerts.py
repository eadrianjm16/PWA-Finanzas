from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..alerts import evaluate_alerts
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return evaluate_alerts(db, user.id)


@router.delete("/{alert_id}", response_model=schemas.MessageResponse)
def dismiss_alert(
    alert_id: str, db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> schemas.MessageResponse:
    if db.get(models.AlertDismissal, (user.id, alert_id)) is None:
        db.add(models.AlertDismissal(user_id=user.id, alert_id=alert_id))
        db.commit()
    return schemas.MessageResponse(message="Alerta descartada")
