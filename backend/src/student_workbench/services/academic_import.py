"""Import a parsed academic schedule into the unified course model.

The academic portal is the authoritative source for courses and the timetable,
so this importer may create the local ``Course`` when no exact match exists.
Re-running the same term is idempotent: entries are upserted by external id and
entries that disappeared from the portal are removed for that term only.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..adapters.kb_parser import ParsedSchedule, ScheduleCell
from ..models import Connection, Course, CourseIdentity, CourseScheduleEntry
from ..timeutil import utcnow
from .courses import normalize_name

PROVIDER = "academic_portal_v1"


def _find_course(session: Session, name: str, term: str | None) -> Course | None:
    target = normalize_name(name)
    candidates = [
        course
        for course in session.scalars(select(Course)).all()
        if normalize_name(course.name) == target and (term is None or course.term == term)
    ]
    return candidates[0] if len(candidates) == 1 else None


def _entry_external_id(course_external_id: str, cell: ScheduleCell) -> str:
    return f"{course_external_id}|{cell.weekday}|{cell.start_time}-{cell.end_time}"


def import_schedule(
    session: Session, connection: Connection, parsed: ParsedSchedule
) -> dict[str, int]:
    created_courses = 0
    created_identities = 0
    upserted_entries = 0
    seen_entry_ids: set[str] = set()

    for external_id, cell in parsed.courses().items():
        identity = session.scalar(
            select(CourseIdentity).where(
                CourseIdentity.connection_id == connection.id,
                CourseIdentity.external_id == external_id,
            )
        )
        course: Course | None = None
        if identity is not None and identity.course_id:
            course = session.get(Course, identity.course_id)

        if course is None:
            course = _find_course(session, cell.course_name, parsed.term_label)
        if course is None:
            course = Course(
                name=cell.course_name,
                normalized_name=normalize_name(cell.course_name),
                term=parsed.term_label,
                teacher=cell.teacher,
            )
            session.add(course)
            session.flush()
            created_courses += 1

        if identity is None:
            identity = CourseIdentity(
                connection_id=connection.id,
                platform="academic",
                provider=PROVIDER,
                external_id=external_id,
                external_name=cell.course_name,
                teacher=cell.teacher,
                course_id=course.id,
                match_status="manual",
            )
            session.add(identity)
            session.flush()
            created_identities += 1
        else:
            identity.external_name = cell.course_name
            identity.teacher = cell.teacher
            identity.course_id = course.id
            identity.match_status = identity.match_status or "manual"
            session.flush()

        for occurrence in parsed.cells:
            if occurrence.external_id != external_id:
                continue
            entry_id = _entry_external_id(external_id, occurrence)
            entry = session.scalar(
                select(CourseScheduleEntry).where(
                    CourseScheduleEntry.connection_id == connection.id,
                    CourseScheduleEntry.external_id == entry_id,
                )
            )
            if entry is None:
                entry = CourseScheduleEntry(
                    connection_id=connection.id,
                    identity_id=identity.id,
                    external_id=entry_id,
                )
                session.add(entry)
            entry.course_id = course.id
            entry.weekday = occurrence.weekday
            entry.start_time = occurrence.start_time
            entry.end_time = occurrence.end_time
            entry.location = occurrence.location
            entry.weeks = list(occurrence.weeks)
            entry.weeks_label = occurrence.weeks_label
            seen_entry_ids.add(entry_id)
            upserted_entries += 1

    removed = 0
    stale = session.scalars(
        select(CourseScheduleEntry).where(
            CourseScheduleEntry.connection_id == connection.id
        )
    ).all()
    for entry in stale:
        if entry.external_id not in seen_entry_ids:
            session.execute(
                delete(CourseScheduleEntry).where(CourseScheduleEntry.id == entry.id)
            )
            removed += 1

    connection.last_sync_at = utcnow()
    connection.status = "ready"
    connection.last_error = None
    session.flush()

    return {
        "courses": len(parsed.courses()),
        "created_courses": created_courses,
        "created_identities": created_identities,
        "entries": upserted_entries,
        "removed_entries": removed,
    }