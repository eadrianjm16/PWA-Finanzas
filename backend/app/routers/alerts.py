from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..alerts import evaluate_alerts
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return evaluate_alerts(db, user.id)
