from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..analysis import build_summary
from ..deps import CurrentUser, get_current_user, get_db_session

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/summary", response_model=schemas.AnalysisSummary)
def get_summary(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc)
    return build_summary(db, user.id, year or now.year, month or now.month)
