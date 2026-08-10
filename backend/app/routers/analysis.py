from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..analysis import build_summary
from ..deps import get_db_session, require_auth

router = APIRouter(prefix="/api/analysis", tags=["analysis"], dependencies=[Depends(require_auth)])


@router.get("/summary", response_model=schemas.AnalysisSummary)
def get_summary(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db_session),
) -> dict:
    now = datetime.now(timezone.utc)
    return build_summary(db, year or now.year, month or now.month)
