from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_tz(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def as_utc(value: datetime, default_tz: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=default_tz)
    return value.astimezone(UTC)


def iso(value: datetime | None, tz: ZoneInfo) -> str | None:
    normalized = ensure_utc(value)
    if normalized is None:
        return None
    return normalized.astimezone(tz).isoformat()


def local_date(value: datetime | None, tz: ZoneInfo) -> date | None:
    normalized = ensure_utc(value)
    if normalized is None:
        return None
    return normalized.astimezone(tz).date()


def local_today(tz: ZoneInfo) -> date:
    return utcnow().astimezone(tz).date()


def date_str(value: date | None) -> str | None:
    return value.isoformat() if value else None
