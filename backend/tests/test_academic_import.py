from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from student_workbench.adapters.kb_parser import ParsedSchedule, parse_kb_html
from student_workbench.models import (
    Connection,
    Course,
    CourseIdentity,
    CourseScheduleEntry,
)
from student_workbench.services.academic_import import import_schedule

FIXTURE = Path(__file__).parent / "fixtures" / "academic_kb_sample.html"


@pytest.fixture(scope="module")
def parsed() -> ParsedSchedule:
    return parse_kb_html(FIXTURE.read_text(encoding="utf-8"))


def _connection(session) -> Connection:
    connection = Connection(
        kind="academic",
        provider="academic_portal_v1",
        display_name="教务系统",
        status="ready",
    )
    session.add(connection)
    session.flush()
    return connection


def test_import_creates_courses_identities_and_entries(session_factory, parsed):
    with session_factory() as session:
        connection = _connection(session)
        result = import_schedule(session, connection, parsed)
        session.commit()

    assert result == {
        "courses": 7,
        "created_courses": 7,
        "created_identities": 7,
        "entries": 7,
        "removed_entries": 0,
    }

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Course)) == 7
        assert session.scalar(select(func.count()).select_from(CourseIdentity)) == 7
        assert session.scalar(select(func.count()).select_from(CourseScheduleEntry)) == 7

        course = session.scalar(select(Course).where(Course.name == "机器学习导论"))
        assert course is not None
        assert course.normalized_name == "机器学习导论"
        assert course.term == "2026-2027学年第一学期"

        identity = session.scalar(
            select(CourseIdentity).where(CourseIdentity.external_id == "机器学习导论|A 24软件 1班")
        )
        assert identity is not None
        assert identity.course_id == course.id
        assert identity.match_status == "manual"

        entry = session.scalar(
            select(CourseScheduleEntry).where(CourseScheduleEntry.course_id == course.id)
        )
        assert entry.weekday == 1
        assert (entry.start_time, entry.end_time) == ("08:00", "09:40")
        assert entry.location == "主5#101"
        assert entry.weeks == list(range(1, 17))


def test_reimport_is_idempotent(session_factory, parsed):
    with session_factory() as session:
        connection = _connection(session)
        import_schedule(session, connection, parsed)
        session.commit()

    with session_factory() as session:
        connection = session.scalar(select(Connection))
        second = import_schedule(session, connection, parsed)
        session.commit()

    assert second["created_courses"] == 0
    assert second["created_identities"] == 0
    assert second["removed_entries"] == 0

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Course)) == 7
        assert session.scalar(select(func.count()).select_from(CourseScheduleEntry)) == 7


def test_entries_removed_when_term_changes(session_factory, parsed):
    with session_factory() as session:
        connection = _connection(session)
        import_schedule(session, connection, parsed)
        session.commit()

    reduced = ParsedSchedule(
        term_label=parsed.term_label,
        term_value=parsed.term_value,
        cells=tuple(cell for cell in parsed.cells if cell.course_name == "编译原理"),
    )

    with session_factory() as session:
        connection = session.scalar(select(Connection))
        result = import_schedule(session, connection, reduced)
        session.commit()

    assert result["removed_entries"] == 6
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(CourseScheduleEntry)) == 1


def test_reuses_existing_course_with_same_name_and_term(session_factory, parsed):
    with session_factory() as session:
        session.add(
            Course(
                name="操作系统",
                normalized_name="操作系统",
                term=parsed.term_label,
                teacher="周老师",
            )
        )
        session.commit()

    with session_factory() as session:
        connection = _connection(session)
        result = import_schedule(session, connection, parsed)
        session.commit()

    assert result["created_courses"] == 6
    with session_factory() as session:
        courses = session.scalars(select(Course).where(Course.name == "操作系统")).all()
        assert len(courses) == 1