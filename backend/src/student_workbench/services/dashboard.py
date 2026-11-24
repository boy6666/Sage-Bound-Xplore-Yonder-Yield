from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Connection,
    Course,
    CourseScheduleEntry,
    PeriodTime,
    Project,
    ScheduleAdjustment,
    SyncRun,
    WorkItem,
)
from ..timeutil import local_date, local_today, utcnow
from .courses import normalize_name
from .projects import project_health
from .settings import current_tz, get_settings_row
from .work_items import ACTIVE_STATUSES, open_count, serialize_item

FAILED_SYNC_STATUSES = ("failed", "needs_auth")


def _sorted_by(items: list[WorkItem], attribute: str) -> list[WorkItem]:
    return sorted(
        items,
        key=lambda item: (
            getattr(item, attribute) is None,
            getattr(item, attribute) or utcnow(),
            item.id,
        ),
    )


def classify_items(
    session: Session, day: date, tz: ZoneInfo, upcoming_days: int
) -> dict[str, list[WorkItem]]:
    items = session.scalars(
        select(WorkItem).where(WorkItem.status.in_(ACTIVE_STATUSES))
    ).unique().all()

    overdue: list[WorkItem] = []
    today_planned: list[WorkItem] = []
    upcoming: list[WorkItem] = []
    blocked: list[WorkItem] = []

    for item in items:
        due = local_date(item.due_at, tz)
        planned_start = local_date(item.planned_start_at, tz)
        if planned_start == day:
            today_planned.append(item)
        elif due is not None and due < day:
            overdue.append(item)
        elif (
            due is not None
            and day <= due
            and (due - day).days <= upcoming_days
            and item.planned_start_at is None
        ):
            upcoming.append(item)
        elif (item.blocked_reason or "").strip():
            blocked.append(item)

    return {
        "overdue": _sorted_by(overdue, "due_at"),
        "today_planned": _sorted_by(today_planned, "planned_start_at"),
        "upcoming_unplanned": _sorted_by(upcoming, "due_at"),
        "blocked": _sorted_by(blocked, "created_at"),
    }


def _period_clock(
    adjustment, period_times: dict[int, tuple[str, str]]
) -> str | None:
    start = period_times.get(adjustment.period_start or 0)
    end = period_times.get(adjustment.period_end or adjustment.period_start or 0)
    if start and end:
        return f"{start[0]}-{end[1]}"
    return None


def _period_detail(adjustment, period_times: dict[int, tuple[str, str]]) -> str:
    label = adjustment.period_label or ""
    clock = _period_clock(adjustment, period_times)
    parts = [f"{label}节" if label else "", clock or ""]
    return " ".join(part for part in parts if part).strip()


def _adjustment_note(
    adjustment, period_times: dict[int, tuple[str, str]]
) -> str:
    return _period_detail(adjustment, period_times) or (
        "停课" if adjustment.kind == "cancel" else "调课"
    )


def _match_adjustment(
    course_name: str, adjustments: list, period_times: dict[int, tuple[str, str]]
) -> tuple[str, str | None]:
    for adjustment in adjustments:
        if adjustment.kind == "makeup":
            continue
        if normalize_name(adjustment.course_name) != normalize_name(course_name):
            continue
        state = "cancelled" if adjustment.kind == "cancel" else "moved"
        return state, _adjustment_note(adjustment, period_times)
    return "normal", None


def classes_today(
    session: Session, day: date, settings_row
) -> tuple[list[dict], bool]:
    term_start = settings_row.term_start_date
    if term_start is None:
        return [], True
    delta_days = (day - term_start).days
    if delta_days < 0:
        return [], False
    week = delta_days // 7 + 1
    weekday = day.isoweekday()

    entries = session.scalars(
        select(CourseScheduleEntry)
        .where(CourseScheduleEntry.course_id.is_not(None))
        .order_by(CourseScheduleEntry.start_time, CourseScheduleEntry.id)
    ).all()

    adjustments = session.scalars(select(ScheduleAdjustment)).all()
    day_adjustments = [
        adjustment
        for adjustment in adjustments
        if (adjustment.adjusted_on is not None and adjustment.adjusted_on == day)
        or (adjustment.week == week and adjustment.weekday == weekday)
    ]
    period_times: dict[int, tuple[str, str]] = {}
    for row in session.scalars(select(PeriodTime)).all():
        period_times.setdefault(row.period, (row.start_time, row.end_time))

    result: list[dict] = []
    for entry in entries:
        if entry.weekday != weekday:
            continue
        if week not in (entry.weeks or []):
            continue
        course = session.get(Course, entry.course_id)
        if course is None:
            continue
        status, note = _match_adjustment(course.name, day_adjustments, period_times)
        result.append(
            {
                "course_id": course.id,
                "course_name": course.name,
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "location": entry.location,
                "open_todos": open_count(session, course_id=course.id),
                "status": status,
                "adjustment_note": note,
            }
        )

    for adjustment in day_adjustments:
        if adjustment.kind != "makeup":
            continue
        start, end = period_times.get(adjustment.period_start or 0, ("", ""))
        if adjustment.period_end:
            end = period_times.get(adjustment.period_end, (start, end))[1] or end
        result.append(
            {
                "course_id": adjustment.course_id or "",
                "course_name": adjustment.course_name,
                "start_time": start,
                "end_time": end,
                "location": adjustment.room,
                "open_todos": (
                    open_count(session, course_id=adjustment.course_id)
                    if adjustment.course_id
                    else 0
                ),
                "status": "makeup",
                "adjustment_note": (
                    f"补课 {_period_detail(adjustment, period_times)}".strip()
                ),
            }
        )

    result.sort(key=lambda item: (item["start_time"] or "99:99", item["course_name"]))
    return result, False


def project_risks(session: Session, tz: ZoneInfo) -> list[dict]:
    projects = session.scalars(select(Project).order_by(Project.created_at, Project.id)).all()
    risks = []
    for project in projects:
        health = project_health(session, project, tz)
        if health["level"] != "red" or not health["reasons"]:
            continue
        reason = health["reasons"][0]
        detail = reason.get("detail")
        text = f"{reason['label']}：{detail}" if detail else reason["label"]
        risks.append(
            {
                "project_id": project.id,
                "name": project.name,
                "level": "red",
                "reason": text,
            }
        )
    return risks


def data_warnings(session: Session, missing_term_start: bool) -> list[str]:
    warnings: list[str] = []
    connections = session.scalars(
        select(Connection).order_by(Connection.created_at, Connection.id)
    ).all()
    for connection in connections:
        latest = session.scalars(
            select(SyncRun)
            .where(SyncRun.connection_id == connection.id)
            .order_by(SyncRun.started_at.desc(), SyncRun.id)
            .limit(1)
        ).first()
        if latest is not None and latest.status in FAILED_SYNC_STATUSES:
            warnings.append(f"{connection.display_name}最近一次同步失败")
        elif connection.last_error and latest is None:
            warnings.append(f"{connection.display_name}最近一次同步失败")
    if missing_term_start:
        warnings.append("缺少学期开始日期，无法确定今日课程")
    return warnings


def build_today(session: Session, day: date | None = None) -> dict:
    settings_row = get_settings_row(session)
    tz = current_tz(session)
    if day is None:
        day = local_today(tz)
    groups = classify_items(session, day, tz, settings_row.upcoming_days)
    classes, missing_term_start = classes_today(session, day, settings_row)
    return {
        "date": day.isoformat(),
        "timezone": settings_row.timezone,
        "classes_today": classes,
        "overdue": [serialize_item(item, tz) for item in groups["overdue"]],
        "today_planned": [
            serialize_item(item, tz) for item in groups["today_planned"]
        ],
        "upcoming_unplanned": [
            serialize_item(item, tz) for item in groups["upcoming_unplanned"]
        ],
        "blocked": [serialize_item(item, tz) for item in groups["blocked"]],
        "project_risks": project_risks(session, tz),
        "data_warnings": data_warnings(session, missing_term_start),
    }
