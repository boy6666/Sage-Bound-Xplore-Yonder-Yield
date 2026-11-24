from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import TodayOut
from ..services.current_week import get_current_week
from ..services.dashboard import build_today
from ..services.settings import current_tz, get_settings_row

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/today", response_model=TodayOut)
def get_today(
    request: Request,
    day: date | None = Query(default=None, alias="date"),
    session: Session = Depends(get_session),
):
    week = None
    if day is None:
        tz = current_tz(session)
        row = get_settings_row(session)
        value = get_current_week(request.app.state.config, session, row, tz)
        week = value.week if value else None
    return build_today(session, day, week=week)
