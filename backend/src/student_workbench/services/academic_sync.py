"""Sync the real academic portal using the locally stored login cookie.

Two pages are read per sync, one request each: the timetable and the
调停补课 page. When the cookie is gone or expired the caller gets
``PLATFORM_AUTH_REQUIRED`` so the UI can open the browser login once and retry.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from ..adapters.academic_http import (
    ScheduleStructureChanged,
    fetch_adjustments_html,
    fetch_schedule_html,
)
from ..adapters.academic_portal_v1 import (
    PortalAuthRequired,
    PortalDependencyMissing,
    PortalError,
    PortalStructureChanged,
    capture_schedule_html,
    default_profile_dir,
)
from ..adapters.adjustments_parser import parse_adjustments_html
from ..adapters.kb_parser import parse_kb_html
from ..adapters.portal_session import (
    load_cookies,
    save_cookies,
    to_httpx_cookies,
)
from ..config import AppConfig
from ..errors import AppError
from ..models import Connection
from ..timeutil import utcnow
from .academic_import import import_adjustments, import_schedule

PROVIDER = "academic_portal_v1"


def _auth_required(message: str) -> AppError:
    return AppError(
        "PLATFORM_AUTH_REQUIRED",
        message,
        409,
        {"provider": PROVIDER},
    )


def _cookie_jar(config: AppConfig):
    stored = load_cookies(config.data_dir)
    if stored is None:
        raise _auth_required("还没有教务登录会话，请先登录一次")
    return stored, to_httpx_cookies(stored.cookies)


def _counts(courses: int, schedule: int, adjustments: int) -> dict[str, int]:
    return {
        "courses": courses,
        "items": 0,
        "schedule": schedule,
        "adjustments": adjustments,
    }


def _import_schedule_html(
    session: Session, connection: Connection, html: str
) -> tuple[int, int]:
    parsed = parse_kb_html(html)
    result = import_schedule(session, connection, parsed)
    return result["courses"], result["entries"]


def _import_adjustments_html(
    session: Session, connection: Connection, html: str
) -> int:
    parsed = parse_adjustments_html(html)
    result = import_adjustments(session, connection, parsed)
    return result["records"]


def sync_from_cookie(
    session: Session, connection: Connection, config: AppConfig
) -> tuple[dict[str, int], str | None]:
    """Read the timetable and the adjustment page with the stored cookie."""
    stored, jar = _cookie_jar(config)

    try:
        schedule_html = fetch_schedule_html(jar)
    except ScheduleStructureChanged as exc:
        raise AppError(
            "PLATFORM_STRUCTURE_CHANGED",
            str(exc),
            409,
            {"provider": PROVIDER},
        ) from exc
    except httpx.HTTPError as exc:
        raise AppError(
            "PLATFORM_NETWORK_ERROR",
            "访问教务系统失败，请检查网络或代理设置",
            409,
            {"provider": PROVIDER},
        ) from exc

    if not schedule_html:
        raise _auth_required("教务登录已失效，需要重新登录")

    courses, schedule = _import_schedule_html(session, connection, schedule_html)
    counts = _counts(courses, schedule, 0)
    warning: str | None = None

    try:
        adjustments_html = fetch_adjustments_html(jar)
    except Exception:  # noqa: BLE001 - timetable already imported
        warning = "调停补课页面请求失败，本次只同步了课程表"
    else:
        if not adjustments_html:
            warning = "调停补课页面需要重新登录，本次只同步了课程表"
        else:
            try:
                counts["adjustments"] = _import_adjustments_html(
                    session, connection, adjustments_html
                )
            except Exception:  # noqa: BLE001 - keep the timetable result
                warning = "调停补课记录解析失败，本次只同步了课程表"

    connection.last_sync_at = utcnow()
    session.flush()
    return counts, warning


def login_with_browser(
    session: Session,
    connection: Connection,
    config: AppConfig,
    *,
    timeout_seconds: int = 600,
) -> dict[str, int]:
    """Open a visible browser, let the user log in, then import and save cookies."""
    profile_dir = default_profile_dir(config.data_dir)
    try:
        html, cookies = asyncio.run(
            capture_schedule_html(
                profile_dir,
                timeout_seconds=timeout_seconds,
                headless=False,
            )
        )
    except PortalAuthRequired as exc:
        raise _auth_required(str(exc)) from exc
    except PortalDependencyMissing as exc:
        raise AppError(
            "PLATFORM_DEPENDENCY_MISSING", str(exc), 409, {"provider": PROVIDER}
        ) from exc
    except PortalStructureChanged as exc:
        raise AppError(
            "PLATFORM_STRUCTURE_CHANGED", str(exc), 409, {"provider": PROVIDER}
        ) from exc
    except PortalError as exc:
        raise AppError(
            "PLATFORM_LOGIN_FAILED", str(exc), 409, {"provider": PROVIDER}
        ) from exc

    saved_at = datetime.now().astimezone().isoformat(timespec="seconds")
    save_cookies(config.data_dir, cookies, saved_at)

    courses, schedule = _import_schedule_html(session, connection, html)
    counts = _counts(courses, schedule, 0)
    try:
        _, jar = _cookie_jar(config)
        adjustments_html = fetch_adjustments_html(jar)
        if adjustments_html:
            counts["adjustments"] = _import_adjustments_html(
                session, connection, adjustments_html
            )
    except Exception:  # noqa: BLE001 - login itself succeeded
        pass

    connection.status = "ready"
    connection.last_error = None
    connection.last_sync_at = utcnow()
    session.flush()
    return counts