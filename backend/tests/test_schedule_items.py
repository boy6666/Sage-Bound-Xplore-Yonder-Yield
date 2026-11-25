from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from student_workbench.models import (
    Connection,
    Course,
    CourseIdentity,
    CourseScheduleEntry,
    WorkItem,
)
from student_workbench.services.courses import schedule_payload
from student_workbench.services.settings import get_settings_row
from student_workbench.timeutil import get_tz

TZ = get_tz("Asia/Shanghai")
TERM_START = date(2026, 9, 7)  # 周一
WEEK2_MONDAY = TERM_START + timedelta(days=7)


def _seed(session, *, with_term_start: bool = True) -> Course:
    course = Course(name="操作系统", normalized_name="操作系统", term="2026-2027-1")
    session.add(course)
    settings = get_settings_row(session)
    if with_term_start:
        settings.term_start_date = TERM_START
    session.flush()
    return course


def _item(
    session,
    title: str,
    *,
    planned: datetime | None = None,
    due: datetime | None = None,
    status: str = "planned",
    course: Course | None = None,
) -> WorkItem:
    item = WorkItem(
        title=title,
        source_type="manual",
        item_type="assignment",
        status=status,
        planned_start_at=planned,
        due_at=due,
        course_id=course.id if course else None,
    )
    session.add(item)
    session.flush()
    return item


def _local_noon(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=TZ).astimezone(UTC)


def test_planned_item_in_week_is_returned_with_weekday(session_factory):
    with session_factory() as session:
        course = _seed(session)
        _item(session, "实验二", planned=_local_noon(WEEK2_MONDAY), course=course)
        session.commit()

        payload = schedule_payload(session, TZ, week=2)

    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["title"] == "实验二"
    assert item["weekday"] == 1
    assert item["course_name"] == "操作系统"
    assert payload["week_start"] == "2026-09-14"


def test_item_outside_the_week_is_excluded(session_factory):
    with session_factory() as session:
        _seed(session)
        _item(session, "下周作业", planned=_local_noon(WEEK2_MONDAY + timedelta(days=8)))
        session.commit()

        payload = schedule_payload(session, TZ, week=2)

    assert payload["items"] == []


def test_completed_and_dismissed_items_are_excluded(session_factory):
    with session_factory() as session:
        _seed(session)
        _item(session, "已完成", planned=_local_noon(WEEK2_MONDAY), status="done")
        _item(session, "已忽略", planned=_local_noon(WEEK2_MONDAY), status="dismissed")
        session.commit()

        payload = schedule_payload(session, TZ, week=2)

    assert payload["items"] == []


def test_due_only_item_uses_due_time_label(session_factory):
    with session_factory() as session:
        _seed(session)
        due = _local_noon(WEEK2_MONDAY + timedelta(days=1))
        _item(session, "截止提醒", due=due, status="inbox")
        session.commit()

        payload = schedule_payload(session, TZ, week=2)

    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["weekday"] == 2
    assert item["time_label"].startswith("截止")


def test_items_are_empty_without_term_start(session_factory):
    with session_factory() as session:
        _seed(session, with_term_start=False)
        _item(session, "实验二", planned=_local_noon(WEEK2_MONDAY))
        session.commit()

        payload = schedule_payload(session, TZ, week=2)

    assert payload["items"] == []
    assert payload["week_start"] is None


def test_default_view_returns_only_the_current_week(session_factory):
    with session_factory() as session:
        course = _seed(session)
        connection = Connection(
            kind="academic",
            provider="academic_portal_v1",
            display_name="教务",
            status="ready",
        )
        session.add(connection)
        session.flush()
        identity = CourseIdentity(
            connection_id=connection.id,
            course_id=course.id,
            platform="academic",
            provider="academic_portal_v1",
            external_id="op|1",
            external_name="操作系统",
            match_status="manual",
        )
        session.add(identity)
        session.flush()
        session.add(
            CourseScheduleEntry(
                connection_id=connection.id,
                identity_id=identity.id,
                course_id=course.id,
                external_id="e1",
                weekday=1,
                start_time="08:00",
                end_time="09:40",
                weeks=[2],
                weeks_label="2周",
            )
        )
        session.commit()

        default_payload = schedule_payload(session, TZ, current_week=12)
        week_payload = schedule_payload(session, TZ, week=2)

    assert default_payload["entries"] == []
    assert len(week_payload["entries"]) == 1


def test_explicit_week_start_overrides_term_start(session_factory):
    with session_factory() as session:
        _seed(session)
        _item(session, "第三周任务", planned=_local_noon(date(2026, 9, 22)))
        session.commit()

        payload = schedule_payload(
            session,
            TZ,
            week_start=date(2026, 9, 21),
            current_week=3,
            week_source="portal",
        )

    assert payload["week_start"] == "2026-09-21"
    assert payload["current_week"] == 3
    assert payload["week_source"] == "portal"
    assert [item["title"] for item in payload["items"]] == ["第三周任务"]
