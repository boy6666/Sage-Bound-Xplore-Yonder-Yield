from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..db import get_session
from ..errors import AppError
from ..schemas import (
    BootstrapComplete,
    BootstrapOut,
    GithubTokenIn,
    GithubTokenOut,
    SettingsOut,
    SettingsPatch,
)
from ..services import credentials
from ..services.settings import (
    get_settings_row,
    settings_out,
    update_settings,
    validate_timezone,
)
from ..services.system import bootstrap_payload

router = APIRouter(prefix="/api/v1", tags=["system"])


def _settings_payload(row) -> dict:
    data = settings_out(row)
    data["github_token_saved"] = bool(credentials.load_github_token())
    return data


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
    return _settings_payload(get_settings_row(session))


@router.patch("/settings", response_model=SettingsOut)
def patch_settings(payload: SettingsPatch, session: Session = Depends(get_session)):
    row = update_settings(session, payload)
    return _settings_payload(row)


@router.put("/settings/github-token", response_model=GithubTokenOut)
def save_github_token(payload: GithubTokenIn):
    if not credentials.save_github_token(payload.token.strip()):
        raise AppError(
            "CREDENTIAL_STORE_FAILED", "无法写入系统凭据库", 500, {}
        )
    return {"saved": True}


@router.delete("/settings/github-token", status_code=204)
def delete_github_token():
    credentials.delete_github_token()
    return Response(status_code=204)