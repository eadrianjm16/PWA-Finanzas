from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import CurrentUser, get_current_user, get_db_session
from ..net_worth import net_worth_history

router = APIRouter(prefix="/api/net-worth", tags=["net-worth"])


@router.get("/history", response_model=list[schemas.NetWorthPointOut])
def get_net_worth_history(
    db: Session = Depends(get_db_session), user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return net_worth_history(db, user.id)
