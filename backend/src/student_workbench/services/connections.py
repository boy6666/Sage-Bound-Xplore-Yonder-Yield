from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import (
    Connection,
    CourseIdentity,
    CourseScheduleEntry,
    SyncRun,
    WorkItem,
)
from ..timeutil import iso
from . import credentials
from .settings import get_settings_row
from .sync.executor import ensure_configured

CHALLENGE_USERNAME = "challenge-user"
CHALLENGE_CODE = "1234"


def get_connection(session: Session, connection_id: str) -> Connection:
    connection = session.get(Connection, connection_id)
    if connection is None:
        raise AppError(
            "NOT_FOUND", "连接不存在", 404, {"connection_id": connection_id}
        )
    return connection


def serialize_connection(connection: Connection, tz: ZoneInfo) -> dict:
    return {
        "id": connection.id,
        "kind": connection.kind,
        "provider": connection.provider,
        "display_name": connection.display_name,
        "status": connection.status,
        "account_label": connection.account_label,
        "last_sync_at": iso(connection.last_sync_at, tz),
        "last_error": connection.last_error,
        "credential_saved": connection.credential_saved,
    }


def list_connections(session: Session, tz: ZoneInfo) -> list[dict]:
    rows = session.scalars(
        select(Connection).order_by(Connection.created_at, Connection.id)
    ).all()
    return [serialize_connection(row, tz) for row in rows]


def start_login(
    session: Session,
    connection: Connection,
    username: str,
    password: str,
    save_password: bool,
) -> dict:
    ensure_configured(connection.provider)
    settings_row = get_settings_row(session)

    connection.account_label = username
    connection.last_error = None

    if save_password:
        saved = credentials.save_password(connection.id, password)
        connection.credential_saved = saved
        if saved:
            settings_row.save_platform_password = True

    if username == CHALLENGE_USERNAME:
        connection.status = "needs_auth"
        connection.challenge_id = str(uuid.uuid4())
        connection.challenge_expected = CHALLENGE_CODE
        session.flush()
        return {
            "status": "challenge",
            "challenge": {
                "id": connection.challenge_id,
                "prompt": "请输入验证码（演示验证码：1234）",
            },
        }

    connection.status = "ready"
    connection.challenge_id = None
    connection.challenge_expected = None
    session.flush()
    return {"status": "ready"}


def submit_challenge(
    session: Session, connection: Connection, challenge_id: str, code: str
) -> dict:
    ensure_configured(connection.provider)
    if (
        not connection.challenge_id
        or connection.challenge_id != challenge_id
        or connection.challenge_expected != code
    ):
        raise AppError(
            "PLATFORM_LOGIN_FAILED",
            "验证码错误或挑战已失效",
            409,
            {"connection_id": connection.id},
        )
    connection.status = "ready"
    connection.challenge_id = None
    connection.challenge_expected = None
    session.flush()
    return {"status": "ready"}


def delete_connection(session: Session, connection: Connection) -> None:
    connection_id = connection.id
    session.execute(
        update(WorkItem)
        .where(WorkItem.connection_id == connection_id)
        .values(connection_id=None, identity_id=None)
    )
    session.execute(
        delete(CourseScheduleEntry).where(
            CourseScheduleEntry.connection_id == connection_id
        )
    )
    session.execute(delete(SyncRun).where(SyncRun.connection_id == connection_id))
    session.execute(
        delete(CourseIdentity).where(CourseIdentity.connection_id == connection_id)
    )
    session.delete(connection)
    session.flush()
