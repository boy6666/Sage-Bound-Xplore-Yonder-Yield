from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from student_workbench.models import (
    Connection,
    Course,
    CourseIdentity,
    CourseScheduleEntry,
    PeriodTime,
    ScheduleAdjustment,
)
from student_workbench.services.dashboard import classes_today
from student_workbench.services.settings import get_settings_row

TERM = "2026-2027学年第一学期"
TERM_START = date(2026, 9, 1)


def _seed(session, day: date, weeks: list[int], course_name: str = "操作系统"):
    connection = Connection(
        kind="academic", provider="academic_portal_v1", display_name="教务", status="ready"
    )
    session.add(connection)
    session.flush()

    course = Course(name=course_name, normalized_name=course_name, term=TERM)
    session.add(course)
    session.flush()

    identity = CourseIdentity(
        connection_id=connection.id,
        course_id=course.id,
        platform="academic",
        provider="academic_portal_v1",
        external_id=f"{course_name}|test",
        external_name=course_name,
        match_status="manual",
    )
    session.add(identity)
    session.flush()

    weekday = day.isoweekday()
    session.add(
        CourseScheduleEntry(
            connection_id=connection.id,
            identity_id=identity.id,
            course_id=course.id,
            external_id=f"{course_name}|{weekday}|08:00-09:40",
            weekday=weekday,
            start_time="08:00",
            end_time="09:40",
            location="主5#418",
            weeks=weeks,
            weeks_label="1-16周(每周)",
        )
    )
    session.add(PeriodTime(term=TERM, period=1, start_time="08:00", end_time="08:45"))
    session.add(PeriodTime(term=TERM, period=2, start_time="08:55", end_time="09:40"))

    settings = get_settings_row(session)
    settings.term_start_date = TERM_START
    session.flush()
    return connection, course


def _week_of(day: date) -> int:
    return (day - TERM_START).days // 7 + 1


def test_cancelled_class_is_marked(session_factory):
    day = TERM_START + timedelta(weeks=11)
    with session_factory() as session:
        connection, _course = _seed(session, day, [_week_of(day)])
        session.add(
            ScheduleAdjustment(
                connection_id=connection.id,
                external_id="a1",
                kind="cancel",
                term=TERM,
                course_name="操作系统",
                course_class="操作系统(24软件)(1班)",
                week=_week_of(day),
                weekday=day.isoweekday(),
                period_label="1-2",
                period_start=1,
                period_end=2,
                adjusted_on=day,
            )
        )
        result, missing = classes_today(session, day, get_settings_row(session))

    assert missing is False
    assert len(result) == 1
    assert result[0]["status"] == "cancelled"
    assert result[0]["adjustment_note"] == "1-2节 08:00-09:40"


def test_moved_class_is_marked(session_factory):
    day = TERM_START + timedelta(weeks=11)
    with session_factory() as session:
        connection, _course = _seed(session, day, [_week_of(day)])
        session.add(
            ScheduleAdjustment(
                connection_id=connection.id,
                external_id="a2",
                kind="move",
                term=TERM,
                course_name="操作系统",
                course_class="操作系统(24软件)(1班)",
                week=_week_of(day),
                weekday=day.isoweekday(),
                period_label="1-2",
                period_start=1,
                period_end=2,
            )
        )
        result, _ = classes_today(session, day, get_settings_row(session))

    assert result[0]["status"] == "moved"


def test_makeup_class_is_added_with_period_times(session_factory):
    day = TERM_START + timedelta(weeks=11)
    with session_factory() as session:
        connection, course = _seed(session, day, [_week_of(day)])
        session.add(
            ScheduleAdjustment(
                connection_id=connection.id,
                external_id="a3",
                kind="makeup",
                term=TERM,
                course_name="操作系统",
                course_class="操作系统(24软件)(1班)",
                weekday=day.isoweekday(),
                period_label="1-2",
                period_start=1,
                period_end=2,
                adjusted_on=day,
                room="主5#418",
                course_id=course.id,
            )
        )
        result, _ = classes_today(session, day, get_settings_row(session))

    assert len(result) == 2
    makeup = next(item for item in result if item["status"] == "makeup")
    assert makeup["course_name"] == "操作系统"
    assert (makeup["start_time"], makeup["end_time"]) == ("08:00", "09:40")
    assert makeup["location"] == "主5#418"


def test_adjustment_for_other_day_is_ignored(session_factory):
    day = TERM_START + timedelta(weeks=11)
    other = day + timedelta(days=1)
    with session_factory() as session:
        connection, _course = _seed(session, day, [_week_of(day)])
        session.add(
            ScheduleAdjustment(
                connection_id=connection.id,
                external_id="a4",
                kind="cancel",
                term=TERM,
                course_name="操作系统",
                course_class="操作系统(24软件)(1班)",
                week=_week_of(other),
                weekday=other.isoweekday(),
            )
        )
        result, _ = classes_today(session, day, get_settings_row(session))

    assert result[0]["status"] == "normal"
    assert result[0]["adjustment_note"] is None


def test_import_adjustments_is_idempotent(session_factory):
    from pathlib import Path

    from student_workbench.adapters.adjustments_parser import parse_adjustments_html
    from student_workbench.services.academic_import import import_adjustments

    fixture = (
        Path(__file__).parent / "fixtures" / "academic_adjustments_sample.html"
    ).read_text(encoding="utf-8")
    parsed = parse_adjustments_html(fixture)

    with session_factory() as session:
        connection = Connection(
            kind="academic", provider="academic_portal_v1", display_name="教务", status="ready"
        )
        session.add(connection)
        session.flush()
        first = import_adjustments(session, connection, parsed)
        session.commit()

    assert first == {"records": 3, "created": 3, "removed": 0}

    with session_factory() as session:
        connection = session.scalar(select(Connection))
        second = import_adjustments(session, connection, parsed)
        session.commit()

    assert second == {"records": 3, "created": 0, "removed": 0}
    with session_factory() as session:
        assert len(session.scalars(select(ScheduleAdjustment)).all()) == 3