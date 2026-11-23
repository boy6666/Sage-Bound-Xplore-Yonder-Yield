from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import BootstrapComplete, BootstrapOut, SettingsOut, SettingsPatch
from ..services.settings import (
    get_settings_row,
    settings_out,
    update_settings,
    validate_timezone,
)
from ..services.system import bootstrap_payload

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/bootstrap", response_model=BootstrapOut)
def get_bootstrap(session: Session = Depends(get_session)):
    return bootstrap_payload(session)


@router.post("/bootstrap/complete", response_model=BootstrapOut)
def complete_bootstrap(
    payload: BootstrapComplete, session: Session = Depends(get_session)
):
    row = get_settings_row(session)
    row.timezone = validate_timezone(payload.timezone)
    if payload.term_start_date is not None:
        row.term_start_date = payload.term_start_date
    row.setup_completed = True
    session.flush()
    return bootstrap_payload(session)


@router.get("/settings", response_model=SettingsOut)
def get_settings(session: Session = Depends(get_session)):
    return settings_out(get_settings_row(session))


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(payload: SettingsPatch, session: Session = Depends(get_session)):
    row = update_settings(session, payload)
    return settings_out(row)
