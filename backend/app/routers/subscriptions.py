from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import CurrentUser, get_current_user, get_db_session
from ..recurring import detect_recurring_charges

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[schemas.RecurringChargeOut])
def list_subscriptions(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return detect_recurring_charges(db, user.id)
