"""Current teaching week, read from the academic portal once per week.

The portal renders ``本学期第N周`` on its home page. That value is stored in
``settings.portal_week`` together with the date it was read, so the app only
visits the portal again after the calendar week changes. Between visits the
stored value is advanced by the number of weeks elapsed.

If the portal cannot be read (no saved cookie, expired session, network error,
page structure change) the stored value keeps being used; only when nothing has
ever been stored does it fall back to ``term_start_date``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..adapters.academic_http import fetch_home_html
from ..adapters.home_parser import parse_current_week
from ..adapters.portal_session import load_cookies, to_httpx_cookies
from ..config import AppConfig
from ..timeutil import local_today

SOURCE_PORTAL = "portal"
SOURCE_CACHED = "cached"
SOURCE_FALLBACK = "fallback"

_failed_on: dict[str, date] = {}


@dataclass(frozen=True)
class CurrentWeek:
    week: int
    week_start: date
    source: str
    captured_on: date | None


def reset_cache() -> None:
    """Forget the in-process failure marker (used by tests)."""
    _failed_on.clear()


def monday_of(day: date) -> date:
    return day - timedelta(days=day.isoweekday() - 1)


def _fallback(settings_row, day: date) -> CurrentWeek | None:
    term_start = getattr(settings_row, "term_start_date", None)
    if term_start is None:
        return None
    delta = (day - term_start).days
    if delta < 0:
        return None
    return CurrentWeek(
        week=delta // 7 + 1,
        week_start=monday_of(day),
        source=SOURCE_FALLBACK,
        captured_on=None,
    )


def _advance(stored_week: int, checked_on: date, day: date) -> int:
    return max(1, stored_week + (day - checked_on).days // 7)


def _read_portal(config: AppConfig) -> int | None:
    stored = load_cookies(config.data_dir)
    if stored is None:
        return None
    try:
        html = fetch_home_html(to_httpx_cookies(stored.cookies))
    except Exception:  # noqa: BLE001 - a failed read must not break the page
        return None
    if not html:
        return None
    return parse_current_week(html)


def get_current_week(
    config: AppConfig, session: Session, settings_row, tz: ZoneInfo
) -> CurrentWeek | None:
    day = local_today(tz)
    monday = monday_of(day)
    stored_week = settings_row.portal_week
    checked_on = settings_row.portal_week_checked_on

    if stored_week is not None and checked_on is not None and monday_of(checked_on) == monday:
        return CurrentWeek(stored_week, monday, SOURCE_PORTAL, checked_on)

    if _failed_on.get("date") != day:
        week = _read_portal(config)
        if week is not None:
            settings_row.portal_week = week
            settings_row.portal_week_checked_on = day
            session.flush()
            session.commit()
            return CurrentWeek(week, monday, SOURCE_PORTAL, day)
        _failed_on["date"] = day

    if stored_week is not None and checked_on is not None:
        return CurrentWeek(
            _advance(stored_week, checked_on, day),
            monday,
            SOURCE_CACHED,
            checked_on,
        )

    return _fallback(settings_row, day)
