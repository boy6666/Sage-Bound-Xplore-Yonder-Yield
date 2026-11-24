"""Sync 超星/学习通 assignments from the aggregate 我的作业 page.

One request returns every assignment across courses. The page does not carry
deadlines, so ``due_at`` stays empty and the user fills it in the inbox.
The workId is stable, which makes repeated syncs idempotent.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters.chaoxing_parser import parse_all_task
from ..adapters.chaoxing_v1 import (
    ChaoxingAuthRequired,
    ChaoxingDependencyMissing,
    ChaoxingError,
    ChaoxingStructureChanged,
    capture_cookies_after_login,
    default_profile_dir,
    fetch_all_task_html,
)
from ..adapters.portal_session import load_cookies, save_cookies, to_httpx_cookies
from ..config import AppConfig
from ..errors import AppError
from ..models import Connection, WorkItem
from ..timeutil import utcnow
from .sync.executor import upsert_identity

PROVIDER = "chaoxing_v1"


def _auth_required(message: str) -> AppError:
    return AppError(
        "PLATFORM_AUTH_REQUIRED", message, 409, {"provider": PROVIDER}
    )


def _cookie_jar(config: AppConfig):
    stored = load_cookies(config.data_dir, PROVIDER)
    if stored is None:
        raise _auth_required("还没有学习通登录会话，请先登录一次")
    return stored, to_httpx_cookies(stored.cookies)


def _course_key(course_id: str | None, course_name: str | None) -> str:
    return course_id or course_name or "unknown"


def sync_from_cookie(
    session: Session, connection: Connection, config: AppConfig
) -> tuple[dict[str, int], str | None]:
    stored, jar = _cookie_jar(config)

    try:
        html = fetch_all_task_html(jar)
    except ChaoxingStructureChanged as exc:
        raise AppError(
            "PLATFORM_STRUCTURE_CHANGED", str(exc), 409, {"provider": PROVIDER}
        ) from exc
    except httpx.HTTPError as exc:
        raise AppError(
            "PLATFORM_NETWORK_ERROR",
            "访问学习通失败，请检查网络或代理设置",
            409,
            {"provider": PROVIDER},
        ) from exc

    if not html:
        raise _auth_required("学习通登录已失效，需要重新登录")

    works = parse_all_task(html)

    identities = {}
    for work in works:
        key = _course_key(work.course_id, work.course_name)
        if key in identities:
            continue
        identities[key] = upsert_identity(
            session,
            connection,
            {
                "external_id": f"chaoxing|{key}",
                "name": work.course_name or "未命名课程",
                "term": None,
                "teacher": None,
            },
        )

    now = utcnow()
    counted = 0
    for work in works:
        identity = identities[_course_key(work.course_id, work.course_name)]
        status = "done" if work.done else "inbox"
        item = session.scalar(
            select(WorkItem).where(
                WorkItem.connection_id == connection.id,
                WorkItem.external_id == work.work_id,
            )
        )
        if item is None:
            item = WorkItem(
                title=work.title,
                item_type="assignment",
                source_type="learning",
                status=status,
                priority="normal",
                due_at=None,
                source_url=work.task_url,
                external_id=work.work_id,
                external_status=work.status,
                identity_id=identity.id,
                course_id=identity.course_id,
                connection_id=connection.id,
                needs_review=False,
                last_synced_at=now,
                completed_at=now if status == "done" else None,
            )
            session.add(item)
        else:
            item.title = work.title
            item.external_status = work.status
            item.source_url = work.task_url
            item.identity_id = identity.id
            item.course_id = identity.course_id
            item.last_synced_at = now
        counted += 1

    connection.last_sync_at = utcnow()
    session.flush()
    return {"courses": len(identities), "items": counted, "schedule": 0}, None


def login_with_browser(
    session: Session,
    connection: Connection,
    config: AppConfig,
    *,
    timeout_seconds: int = 600,
) -> dict[str, int]:
    profile_dir = default_profile_dir(config.data_dir)
    try:
        cookies = asyncio.run(
            capture_cookies_after_login(
                profile_dir, timeout_seconds=timeout_seconds
            )
        )
    except ChaoxingAuthRequired as exc:
        raise _auth_required(str(exc)) from exc
    except ChaoxingDependencyMissing as exc:
        raise AppError(
            "PLATFORM_DEPENDENCY_MISSING", str(exc), 409, {"provider": PROVIDER}
        ) from exc
    except ChaoxingError as exc:
        raise AppError(
            "PLATFORM_LOGIN_FAILED", str(exc), 409, {"provider": PROVIDER}
        ) from exc

    saved_at = datetime.now().astimezone().isoformat(timespec="seconds")
    save_cookies(config.data_dir, cookies, saved_at, PROVIDER)

    counts, _ = sync_from_cookie(session, connection, config)
    connection.status = "ready"
    connection.last_error = None
    connection.last_sync_at = utcnow()
    session.flush()
    return counts