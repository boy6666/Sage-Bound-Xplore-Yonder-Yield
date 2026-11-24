from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from student_workbench.models import Connection, Course, CourseIdentity, WorkItem
from student_workbench.services import chaoxing_sync
from student_workbench.services.courses import normalize_name
from student_workbench.services.sync.executor import start_sync

FIXTURE = (Path(__file__).parent / "fixtures" / "chaoxing_all_task.html").read_text(
    encoding="utf-8"
)


@pytest.fixture
def connection(session_factory):
    with session_factory() as session:
        row = Connection(
            kind="learning",
            provider="chaoxing_v1",
            display_name="学习通",
            status="ready",
        )
        session.add(row)
        session.commit()
        return row.id


def _stub(monkeypatch, html: str = FIXTURE):
    monkeypatch.setattr(
        chaoxing_sync,
        "load_cookies",
        lambda data_dir, provider=None: SimpleNamespace(
            cookies=[{"name": "cx", "value": "1"}], saved_at="now"
        ),
    )
    monkeypatch.setattr(chaoxing_sync, "to_httpx_cookies", lambda cookies: {})
    monkeypatch.setattr(chaoxing_sync, "fetch_all_task_html", lambda jar: html)


def test_sync_imports_courses_and_statuses(
    app, session_factory, connection, monkeypatch
):
    _stub(monkeypatch)
    with session_factory() as session:
        for name in ("示例课程A", "示例课程B"):
            session.add(Course(name=name, normalized_name=normalize_name(name)))
        session.commit()

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

    assert run.status == "succeeded"
    assert run.counts_json["courses"] == 2
    assert run.counts_json["items"] == 3

    with session_factory() as session:
        items = {item.external_id: item for item in session.query(WorkItem).all()}
        assert items["50001"].status == "inbox"  # 未提交
        assert items["50002"].status == "done"  # 待批阅 = 已提交
        assert items["50003"].status == "done"  # 已完成
        assert items["50001"].course_id is not None
        assert session.query(CourseIdentity).count() == 2
        assert {identity.match_status for identity in session.query(CourseIdentity)} == {
            "auto_exact"
        }


def test_second_sync_is_idempotent(app, session_factory, connection, monkeypatch):
    _stub(monkeypatch)

    with session_factory() as session:
        row = session.get(Connection, connection)
        start_sync(session, row, app.state.config)
        session.commit()

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

    assert run.counts_json["items"] == 3
    with session_factory() as session:
        assert session.query(WorkItem).count() == 3
        assert session.query(CourseIdentity).count() == 2


def test_sync_keeps_local_plan(app, session_factory, connection, monkeypatch):
    _stub(monkeypatch)

    with session_factory() as session:
        row = session.get(Connection, connection)
        start_sync(session, row, app.state.config)
        session.commit()

    with session_factory() as session:
        item = session.query(WorkItem).filter_by(external_id="50001").one()
        item.status = "planned"
        item.notes = "本地备注"
        session.commit()

    with session_factory() as session:
        row = session.get(Connection, connection)
        start_sync(session, row, app.state.config)
        session.commit()

    with session_factory() as session:
        item = session.query(WorkItem).filter_by(external_id="50001").one()
        assert item.status == "planned"
        assert item.notes == "本地备注"


def test_missing_cookie_marks_needs_auth(
    app, session_factory, connection, monkeypatch
):
    monkeypatch.setattr(
        chaoxing_sync, "load_cookies", lambda data_dir, provider=None: None
    )

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

    assert run.status == "failed"
    assert run.error_code == "PLATFORM_AUTH_REQUIRED"
    assert row.status == "needs_auth"


def test_expired_session_marks_needs_auth(
    app, session_factory, connection, monkeypatch
):
    _stub(monkeypatch, html="")

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

    assert run.error_code == "PLATFORM_AUTH_REQUIRED"
    assert row.status == "needs_auth"