from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from student_workbench.errors import AppError
from student_workbench.models import Connection, CourseScheduleEntry, ScheduleAdjustment
from student_workbench.services import academic_sync
from student_workbench.services.sync.executor import start_sync

FIXTURES = Path(__file__).parent / "fixtures"
KB_HTML = (FIXTURES / "academic_kb_sample.html").read_text(encoding="utf-8")
TBK_HTML = (FIXTURES / "academic_adjustments_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def connection(session_factory):
    with session_factory() as session:
        row = Connection(
            kind="academic",
            provider="academic_portal_v1",
            display_name="教务系统",
            status="ready",
        )
        session.add(row)
        session.commit()
        return row.id


def _stub_cookie(monkeypatch):
    monkeypatch.setattr(
        academic_sync,
        "load_cookies",
        lambda data_dir: SimpleNamespace(cookies={"PHPSESSID": "x"}, saved_at="now"),
    )
    monkeypatch.setattr(academic_sync, "to_httpx_cookies", lambda cookies: {})


def test_sync_imports_schedule_and_adjustments(
    app, session_factory, connection, monkeypatch
):
    _stub_cookie(monkeypatch)
    monkeypatch.setattr(academic_sync, "fetch_schedule_html", lambda jar: KB_HTML)
    monkeypatch.setattr(academic_sync, "fetch_adjustments_html", lambda jar: TBK_HTML)

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

        assert run.status == "succeeded"
        assert run.counts_json["schedule"] > 0
        assert run.counts_json["courses"] > 0
        assert row.status == "ready"

    with session_factory() as session:
        assert session.query(CourseScheduleEntry).count() > 0
        assert session.query(ScheduleAdjustment).count() > 0


def test_missing_cookie_marks_connection_needs_auth(
    app, session_factory, connection, monkeypatch
):
    monkeypatch.setattr(academic_sync, "load_cookies", lambda data_dir: None)

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

        assert run.status == "failed"
        assert run.error_code == "PLATFORM_AUTH_REQUIRED"
        assert row.status == "needs_auth"


def test_expired_session_marks_connection_needs_auth(
    app, session_factory, connection, monkeypatch
):
    _stub_cookie(monkeypatch)
    monkeypatch.setattr(academic_sync, "fetch_schedule_html", lambda jar: "")

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

        assert run.status == "failed"
        assert run.error_code == "PLATFORM_AUTH_REQUIRED"
        assert row.status == "needs_auth"


def test_adjustment_failure_keeps_schedule_and_marks_partial(
    app, session_factory, connection, monkeypatch
):
    _stub_cookie(monkeypatch)
    monkeypatch.setattr(academic_sync, "fetch_schedule_html", lambda jar: KB_HTML)

    def boom(jar):
        raise RuntimeError("network down")

    monkeypatch.setattr(academic_sync, "fetch_adjustments_html", boom)

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

        assert run.status == "partial"
        assert "调停补课" in (run.error_message or "")
        assert run.counts_json["schedule"] > 0
        assert row.status == "ready"

    with session_factory() as session:
        assert session.query(CourseScheduleEntry).count() > 0


def test_browser_login_requires_academic_provider(client, session_factory):
    with session_factory() as session:
        row = Connection(
            kind="learning", provider="learning_fake", display_name="示例", status="ready"
        )
        session.add(row)
        session.commit()
        connection_id = row.id

    response = client.post(f"/api/v1/connections/{connection_id}/browser-login")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PLATFORM_NOT_CONFIGURED"


def test_sync_endpoint_accepts_academic_portal_provider(
    app, client, session_factory, connection, monkeypatch
):
    _stub_cookie(monkeypatch)
    monkeypatch.setattr(academic_sync, "fetch_schedule_html", lambda jar: "")
    with session_factory() as session:
        session.get(Connection, connection).status = "ready"
        session.commit()

    response = client.post(f"/api/v1/connections/{connection}/sync")
    assert response.status_code == 202
    assert "sync_run_id" in response.json()


def test_unknown_provider_still_rejected():
    from student_workbench.services.sync.executor import ensure_configured

    with pytest.raises(AppError) as excinfo:
        ensure_configured("unknown_provider")
    assert excinfo.value.code == "PLATFORM_NOT_CONFIGURED"


def test_chaoxing_provider_is_configured():
    from student_workbench.services.sync.executor import ensure_configured

    ensure_configured("chaoxing_v1")


def test_missing_browser_dependency_has_its_own_code(
    app, session_factory, connection, monkeypatch
):
    from student_workbench.adapters.academic_portal_v1 import PortalDependencyMissing

    async def fake_capture(*args, **kwargs):
        raise PortalDependencyMissing("未安装 Playwright")

    monkeypatch.setattr(academic_sync, "capture_schedule_html", fake_capture)

    with session_factory() as session:
        row = session.get(Connection, connection)
        with pytest.raises(AppError) as excinfo:
            academic_sync.login_with_browser(session, row, app.state.config)

    assert excinfo.value.code == "PLATFORM_DEPENDENCY_MISSING"
    assert "Playwright" in excinfo.value.message


def test_network_failure_has_its_own_code(
    app, session_factory, connection, monkeypatch
):
    import httpx

    _stub_cookie(monkeypatch)

    def boom(jar):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(academic_sync, "fetch_schedule_html", boom)

    with session_factory() as session:
        row = session.get(Connection, connection)
        run = start_sync(session, row, app.state.config)
        session.commit()

    assert run.status == "failed"
    assert run.error_code == "PLATFORM_NETWORK_ERROR"