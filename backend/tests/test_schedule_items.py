from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from student_workbench.models import Course, WorkItem
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
