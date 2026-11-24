from __future__ import annotations

import re
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import (
    Course,
    CourseIdentity,
    CourseScheduleEntry,
    WorkItem,
)
from ..schemas import CourseCreate
from ..timeutil import date_str, ensure_utc, iso, local_date, local_today
from .settings import get_settings_row
from .work_items import ACTIVE_STATUSES, open_count, serialize_item

_PUNCTUATION = re.compile(r"[\s\-_/\\.,，。·:：()（）\[\]【】]+")


def normalize_name(name: str) -> str:
    return _PUNCTUATION.sub("", name.strip().lower())


def get_course(session: Session, course_id: str) -> Course:
    course = session.get(Course, course_id)
    if course is None:
        raise AppError("NOT_FOUND", "课程不存在", 404, {"course_id": course_id})
    return course


def create_course(session: Session, payload: CourseCreate) -> Course:
    course = Course(
        name=payload.name,
        normalized_name=normalize_name(payload.name),
        code=payload.code,
        term=payload.term,
        teacher=payload.teacher,
    )
    session.add(course)
    session.flush()
    return course


def serialize_identity(identity: CourseIdentity) -> dict:
    return {
        "id": identity.id,
        "connection_id": identity.connection_id,
        "platform": identity.platform,
        "provider": identity.provider,
        "external_id": identity.external_id,
        "external_name": identity.external_name,
        "teacher": identity.teacher,
        "match_status": identity.match_status,
        "course_id": identity.course_id,
    }


def serialize_entry(session: Session, entry: CourseScheduleEntry) -> dict:
    course = session.get(Course, entry.course_id) if entry.course_id else None
    return {
        "id": entry.id,
        "course_id": entry.course_id or "",
        "course_name": course.name if course else "",
        "weekday": entry.weekday,
        "start_time": entry.start_time,
        "end_time": entry.end_time,
        "location": entry.location,
        "weeks": list(entry.weeks or []),
        "weeks_label": entry.weeks_label,
    }


def course_identities(session: Session, course_id: str) -> list[CourseIdentity]:
    return list(
        session.scalars(
            select(CourseIdentity)
            .where(CourseIdentity.course_id == course_id)
            .order_by(CourseIdentity.created_at, CourseIdentity.id)
        ).all()
    )


def course_entries(session: Session, course_id: str) -> list[CourseScheduleEntry]:
    return list(
        session.scalars(
            select(CourseScheduleEntry)
            .where(CourseScheduleEntry.course_id == course_id)
            .order_by(CourseScheduleEntry.weekday, CourseScheduleEntry.start_time)
        ).all()
    )


def next_class(entries: list[CourseScheduleEntry], tz: ZoneInfo) -> dict | None:
    if not entries:
        return None
    today = local_today(tz).isoweekday()
    ordered = sorted(entries, key=lambda entry: (entry.weekday, entry.start_time))
    selected = next(
        (entry for entry in ordered if entry.weekday >= today), ordered[0]
    )
    return {
        "weekday": selected.weekday,
        "start_time": selected.start_time,
        "end_time": selected.end_time,
        "location": selected.location,
    }


def serialize_course(session: Session, course: Course, tz: ZoneInfo) -> dict:
    entries = course_entries(session, course.id)
    return {
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "term": course.term,
        "teacher": course.teacher,
        "identities": [serialize_identity(item) for item in course_identities(session, course.id)],
        "open_todos": open_count(session, course_id=course.id),
        "next_class": next_class(entries, tz),
    }


def list_courses(session: Session, tz: ZoneInfo) -> list[dict]:
    courses = session.scalars(select(Course).order_by(Course.created_at, Course.id)).all()
    return [serialize_course(session, course, tz) for course in courses]


def course_detail(session: Session, course: Course, tz: ZoneInfo) -> dict:
    todos = session.scalars(
        select(WorkItem)
        .where(
            WorkItem.course_id == course.id,
            WorkItem.status.in_(ACTIVE_STATUSES),
        )
        .order_by(WorkItem.created_at, WorkItem.id)
    ).unique().all()
    return {
        "course": serialize_course(session, course, tz),
        "schedule": [
            serialize_entry(session, entry) for entry in course_entries(session, course.id)
        ],
        "todos": [serialize_item(item, tz) for item in todos],
    }


def week_start_for(term_start: date, week: int) -> date:
    return term_start + timedelta(days=(week - 1) * 7)


def _hhmm(value, tz: ZoneInfo) -> str:
    normalized = ensure_utc(value)
    if normalized is None:
        return ''
    return normalized.astimezone(tz).strftime('%H:%M')


def _schedule_items(
    session: Session, tz: ZoneInfo, week_start: date
) -> list[dict]:
    rows = session.scalars(
        select(WorkItem)
        .where(WorkItem.status.not_in(("done", "dismissed")))
        .order_by(WorkItem.id)
    ).unique().all()

    course_ids = {row.course_id for row in rows if row.course_id}
    names: dict[str, str] = {}
    if course_ids:
        names = {
            course.id: course.name
            for course in session.scalars(
                select(Course).where(Course.id.in_(course_ids))
            )
        }

    items: list[dict] = []
    for row in rows:
        planned = row.planned_start_at is not None
        anchor = row.planned_start_at if planned else row.due_at
        anchor_date = local_date(anchor, tz)
        if anchor_date is None:
            continue
        offset = (anchor_date - week_start).days
        if offset < 0 or offset > 6:
            continue
        clock = _hhmm(anchor, tz)
        items.append(
            {
                "id": row.id,
                "title": row.title,
                "weekday": offset + 1,
                "kind": "planned" if planned else "due",
                "time_label": clock if planned else f"截止 {clock}",
                "item_type": row.item_type,
                "priority": row.priority,
                "status": row.status,
                "course_id": row.course_id,
                "course_name": names.get(row.course_id) if row.course_id else None,
                "due_at": iso(row.due_at, tz),
                "planned_start_at": iso(row.planned_start_at, tz),
            }
        )

    items.sort(key=lambda item: (item["weekday"], item["time_label"]))
    return items


def schedule_payload(
    session: Session, tz: ZoneInfo, week: int | None = None
) -> dict:
    settings_row = get_settings_row(session)
    term_start = settings_row.term_start_date
    entries = session.scalars(
        select(CourseScheduleEntry)
        .where(CourseScheduleEntry.course_id.is_not(None))
        .order_by(
            CourseScheduleEntry.weekday,
            CourseScheduleEntry.start_time,
            CourseScheduleEntry.id,
        )
    ).all()
    if week is not None:
        entries = [entry for entry in entries if week in (entry.weeks or [])]
    current_week = None
    if term_start is not None:
        today = local_today(tz)
        delta_days = (today - term_start).days
        if delta_days >= 0:
            current_week = delta_days // 7 + 1

    week_start = None
    items: list[dict] = []
    if term_start is not None:
        target_week = week if week is not None else current_week
        if target_week is not None:
            week_start = week_start_for(term_start, target_week)
            items = _schedule_items(session, tz, week_start)

    return {
        "term_start_date": date_str(term_start),
        "current_week": current_week,
        "week_start": date_str(week_start),
        "entries": [serialize_entry(session, entry) for entry in entries],
        "items": items,
        "missing_term_start": term_start is None,
    }


def unmatched_identities(session: Session) -> list[dict]:
    identities = session.scalars(
        select(CourseIdentity)
        .where(CourseIdentity.match_status == "unmatched")
        .order_by(CourseIdentity.created_at, CourseIdentity.id)
    ).all()
    all_courses = session.scalars(select(Course)).all()
    items = []
    for identity in identities:
        normalized = normalize_name(identity.external_name)
        suggested = [
            {
                "course_id": course.id,
                "name": course.name,
                "reason": "名称完全匹配",
            }
            for course in all_courses
            if course.normalized_name == normalized
        ]
        items.append(
            {
                "identity": serialize_identity(identity),
                "provider": identity.provider,
                "suggested": suggested,
            }
        )
    return items


def get_identity(session: Session, identity_id: str) -> CourseIdentity:
    identity = session.get(CourseIdentity, identity_id)
    if identity is None:
        raise AppError(
            "NOT_FOUND", "课程身份不存在", 404, {"identity_id": identity_id}
        )
    return identity


def link_identity(session: Session, identity: CourseIdentity, course_id: str) -> CourseIdentity:
    course = get_course(session, course_id)
    identity.course_id = course.id
    identity.match_status = "manual"
    session.execute(
        update(CourseScheduleEntry)
        .where(CourseScheduleEntry.identity_id == identity.id)
        .values(course_id=course.id)
    )
    session.execute(
        update(WorkItem)
        .where(WorkItem.identity_id == identity.id)
        .values(course_id=course.id)
    )
    session.flush()
    return identity


def unlink_identity(session: Session, identity: CourseIdentity) -> CourseIdentity:
    identity.course_id = None
    identity.match_status = "unmatched"
    session.execute(
        update(CourseScheduleEntry)
        .where(CourseScheduleEntry.identity_id == identity.id)
        .values(course_id=None)
    )
    session.execute(
        update(WorkItem)
        .where(WorkItem.identity_id == identity.id)
        .values(course_id=None)
    )
    session.flush()
    return identity


def create_course_from_identity(
    session: Session, identity: CourseIdentity, name: str
) -> Course:
    course = Course(
        name=name,
        normalized_name=normalize_name(name),
        teacher=identity.teacher,
    )
    session.add(course)
    session.flush()
    identity.course_id = course.id
    identity.match_status = "manual"
    session.execute(
        update(CourseScheduleEntry)
        .where(CourseScheduleEntry.identity_id == identity.id)
        .values(course_id=course.id)
    )
    session.execute(
        update(WorkItem)
        .where(WorkItem.identity_id == identity.id)
        .values(course_id=course.id)
    )
    session.flush()
    return course


def match_course(
    session: Session, name: str, term: str | None, teacher: str | None
) -> Course | None:
    normalized = normalize_name(name)
    candidates = [
        course
        for course in session.scalars(select(Course)).all()
        if course.normalized_name == normalized
    ]
    if term:
        candidates = [course for course in candidates if course.term in (None, term)]
    if teacher:
        refined = [
            course
            for course in candidates
            if not course.teacher or course.teacher == teacher
        ]
        if refined:
            candidates = refined
    if len(candidates) == 1:
        return candidates[0]
    return None
