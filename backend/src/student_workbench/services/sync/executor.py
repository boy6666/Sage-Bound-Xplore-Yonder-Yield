from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import AppError
from ...models import Connection, CourseIdentity, CourseScheduleEntry, SyncRun, WorkItem
from ...timeutil import as_utc, iso, utcnow
from .. import academic_sync
from ..courses import match_course
from ..settings import current_tz
from . import fake

REAL_PROVIDERS = {"academic_portal_v1", "chaoxing_v1"}
FAKE_PROVIDERS = {"academic_fake", "learning_fake"}
ACTIVE_RUN_STATUSES = ("running",)


def ensure_configured(provider: str) -> None:
    if provider == "academic_portal_v1":
        return
    if provider in REAL_PROVIDERS:
        raise AppError(
            "PLATFORM_NOT_CONFIGURED",
            "该平台适配器尚未配置",
            409,
            {"provider": provider},
        )
    if provider not in FAKE_PROVIDERS:
        raise AppError(
            "PLATFORM_NOT_CONFIGURED",
            "未知平台适配器",
            409,
            {"provider": provider},
        )


def _parse_due(value: str, tz: ZoneInfo) -> datetime:
    parsed = datetime.fromisoformat(value)
    return as_utc(parsed, tz)


def _active_run(session: Session, connection_id: str) -> SyncRun | None:
    return session.scalars(
        select(SyncRun)
        .where(
            SyncRun.connection_id == connection_id,
            SyncRun.status.in_(ACTIVE_RUN_STATUSES),
        )
        .order_by(SyncRun.started_at.desc(), SyncRun.id)
        .limit(1)
    ).first()


def _upsert_identity(
    session: Session, connection: Connection, external: dict
) -> CourseIdentity:
    identity = session.scalar(
        select(CourseIdentity).where(
            CourseIdentity.connection_id == connection.id,
            CourseIdentity.external_id == external["external_id"],
        )
    )
    if identity is None:
        identity = CourseIdentity(
            connection_id=connection.id,
            platform=connection.kind,
            provider=connection.provider,
            external_id=external["external_id"],
            external_name=external["name"],
            teacher=external.get("teacher"),
            match_status="unmatched",
        )
        session.add(identity)
        session.flush()
    else:
        identity.external_name = external["name"]
        identity.teacher = external.get("teacher")
        identity.platform = connection.kind
        identity.provider = connection.provider

    if identity.match_status == "unmatched":
        course = match_course(
            session,
            external["name"],
            external.get("term"),
            external.get("teacher"),
        )
        if course is not None:
            identity.course_id = course.id
            identity.match_status = "auto_exact"
    session.flush()
    return identity


def _upsert_schedule(
    session: Session,
    connection: Connection,
    identity: CourseIdentity,
    external: dict,
) -> CourseScheduleEntry:
    entry = session.scalar(
        select(CourseScheduleEntry).where(
            CourseScheduleEntry.connection_id == connection.id,
            CourseScheduleEntry.external_id == external["external_id"],
        )
    )
    weeks = fake.weeks_for(
        external["start_week"], external["end_week"], external["pattern"]
    )
    label = fake.weeks_label(
        external["start_week"], external["end_week"], external["pattern"]
    )
    if entry is None:
        entry = CourseScheduleEntry(
            connection_id=connection.id,
            identity_id=identity.id,
            external_id=external["external_id"],
        )
        session.add(entry)
    entry.course_id = identity.course_id
    entry.weekday = external["weekday"]
    entry.start_time = external["start_time"]
    entry.end_time = external["end_time"]
    entry.location = external["location"]
    entry.weeks = weeks
    entry.weeks_label = label
    session.flush()
    return entry


def _sync_academic(session: Session, connection: Connection) -> dict[str, int]:
    identities: dict[str, CourseIdentity] = {}
    for external in fake.ACADEMIC_COURSES:
        identities[external["external_id"]] = _upsert_identity(
            session, connection, external
        )

    schedule_count = 0
    for course_external_id, entries in fake.ACADEMIC_SCHEDULE.items():
        identity = identities[course_external_id]
        for entry in entries:
            _upsert_schedule(session, connection, identity, entry)
            schedule_count += 1

    return {"courses": len(identities), "items": 0, "schedule": schedule_count}


def _map_external_status(external_status: str) -> str:
    if external_status in ("submitted", "graded"):
        return "done"
    return "inbox"


def _sync_learning(session: Session, connection: Connection) -> dict[str, int]:
    tz = current_tz(session)
    identities: dict[str, CourseIdentity] = {}
    for external in fake.LEARNING_COURSES:
        identities[external["external_id"]] = _upsert_identity(
            session, connection, external
        )

    now = utcnow()
    item_count = 0
    for external in fake.LEARNING_ASSIGNMENTS:
        identity = identities[external["course_external_id"]]
        item = session.scalar(
            select(WorkItem).where(
                WorkItem.connection_id == connection.id,
                WorkItem.external_id == external["external_id"],
            )
        )
        due_at = _parse_due(external["due_at"], tz)
        if item is None:
            status = _map_external_status(external["external_status"])
            item = WorkItem(
                title=external["title"],
                notes=external.get("description"),
                item_type="assignment",
                source_type="learning",
                status=status,
                priority="normal",
                due_at=due_at,
                source_url=external.get("source_url"),
                external_id=external["external_id"],
                external_status=external["external_status"],
                identity_id=identity.id,
                course_id=identity.course_id,
                connection_id=connection.id,
                needs_review=False,
                last_synced_at=now,
                completed_at=now if status == "done" else None,
            )
            session.add(item)
        else:
            item.title = external["title"]
            item.due_at = due_at
            item.source_url = external.get("source_url")
            item.external_status = external["external_status"]
            item.course_id = identity.course_id
            item.identity_id = identity.id
            item.last_synced_at = now
        session.flush()
        item_count += 1

    return {"courses": len(identities), "items": item_count, "schedule": 0}


def _execute(
    session: Session, connection: Connection, config
) -> tuple[dict[str, int], str | None]:
    if connection.provider == "academic_fake":
        return _sync_academic(session, connection), None
    if connection.provider == "learning_fake":
        return _sync_learning(session, connection), None
    if connection.provider == "academic_portal_v1":
        return academic_sync.sync_from_cookie(session, connection, config)
    raise AppError(
        "PLATFORM_NOT_CONFIGURED", "该平台适配器尚未配置", 409, {"provider": connection.provider}
    )


def start_sync(session: Session, connection: Connection, config) -> SyncRun:
    ensure_configured(connection.provider)
    active = _active_run(session, connection.id)
    if active is not None:
        return active
    if connection.status != "ready":
        raise AppError(
            "PLATFORM_AUTH_REQUIRED",
            "请先登录该平台",
            409,
            {"connection_id": connection.id, "status": connection.status},
        )

    run = SyncRun(
        connection_id=connection.id,
        status="running",
        started_at=utcnow(),
        counts_json={"courses": 0, "items": 0, "schedule": 0},
    )
    session.add(run)
    session.flush()

    try:
        counts, warning = _execute(session, connection, config)
    except AppError as exc:
        run.status = "failed"
        run.error_code = exc.code
        run.error_message = exc.message
        if exc.code == "PLATFORM_AUTH_REQUIRED":
            connection.status = "needs_auth"
        else:
            connection.status = "error"
        connection.last_error = exc.message
    except Exception as exc:  # pragma: no cover - defensive
        run.status = "failed"
        run.error_code = "PLATFORM_STRUCTURE_CHANGED"
        run.error_message = str(exc)[:500]
        connection.status = "error"
        connection.last_error = run.error_message
    else:
        run.counts_json = counts
        if warning:
            run.status = "partial"
            run.error_message = warning
        else:
            run.status = "succeeded"
        connection.status = "ready"
        connection.last_error = None
        connection.last_sync_at = utcnow()
    run.finished_at = utcnow()
    session.flush()
    return run


def get_run(session: Session, run_id: str) -> SyncRun:
    run = session.get(SyncRun, run_id)
    if run is None:
        raise AppError("NOT_FOUND", "同步记录不存在", 404, {"sync_run_id": run_id})
    return run


def list_runs(session: Session, limit: int = 20) -> list[SyncRun]:
    return session.scalars(
        select(SyncRun).order_by(SyncRun.started_at.desc(), SyncRun.id).limit(limit)
    ).all()


def serialize_run(session: Session, run: SyncRun, tz: ZoneInfo) -> dict:
    connection = session.get(Connection, run.connection_id)
    return {
        "id": run.id,
        "connection_id": run.connection_id,
        "connection_name": connection.display_name if connection else "",
        "kind": connection.kind if connection else "",
        "status": run.status,
        "started_at": iso(run.started_at, tz),
        "finished_at": iso(run.finished_at, tz),
        "counts": {
            "courses": int(run.counts_json.get("courses", 0)),
            "items": int(run.counts_json.get("items", 0)),
            "schedule": int(run.counts_json.get("schedule", 0)),
            "adjustments": int(run.counts_json.get("adjustments", 0)),
        },
        "error_code": run.error_code,
        "error_message": run.error_message,
    }
