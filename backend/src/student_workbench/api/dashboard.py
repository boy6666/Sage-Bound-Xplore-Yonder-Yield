from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import TodayOut
from ..services.dashboard import build_today

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/today", response_model=TodayOut)
def get_today(
    day: date | None = Query(default=None, alias="date"),
    session: Session = Depends(get_session),
):
    return build_today(session, day)
