from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..alerts import evaluate_alerts
from ..deps import get_db_session, require_auth

router = APIRouter(prefix="/api/alerts", tags=["alerts"], dependencies=[Depends(require_auth)])


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(db: Session = Depends(get_db_session)) -> list[dict]:
    return evaluate_alerts(db)
