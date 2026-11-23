from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import Settings
from ..schemas import SettingsPatch
from ..timeutil import date_str, get_tz

SETTINGS_ID = 1


def get_settings_row(session: Session) -> Settings:
    row = session.get(Settings, SETTINGS_ID)
    if row is None:
        row = Settings(id=SETTINGS_ID)
        session.add(row)
        session.flush()
    return row


def current_tz(session: Session) -> ZoneInfo:
    return get_tz(get_settings_row(session).timezone)


def settings_out(row: Settings) -> dict:
    return {
        "setup_completed": row.setup_completed,
        "timezone": row.timezone,
        "upcoming_days": row.upcoming_days,
        "stale_snapshot_hours": row.stale_snapshot_hours,
        "inactive_days": row.inactive_days,
        "save_platform_password": row.save_platform_password,
        "term_start_date": date_str(row.term_start_date),
    }


def validate_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AppError(
            "VALIDATION_ERROR",
            "时区不合法",
            422,
            {"field": "timezone", "value": name},
        ) from exc
    return name


def update_settings(session: Session, payload: SettingsPatch) -> Settings:
    row = get_settings_row(session)
    data = payload.model_dump(exclude_unset=True)
    if "timezone" in data and data["timezone"] is not None:
        row.timezone = validate_timezone(data["timezone"])
    for field in (
        "upcoming_days",
        "stale_snapshot_hours",
        "inactive_days",
        "save_platform_password",
        "term_start_date",
    ):
        if field in data:
            setattr(row, field, data[field])
    session.flush()
    return row
