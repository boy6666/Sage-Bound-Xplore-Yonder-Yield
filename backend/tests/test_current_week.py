from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from student_workbench.services import current_week as week_service
from student_workbench.services.current_week import get_current_week
from student_workbench.services.settings import get_settings_row
from student_workbench.timeutil import get_tz

TZ = get_tz("Asia/Shanghai")
DAY1 = date(2026, 11, 24)  # 周二
DAY2 = date(2026, 12, 1)  # 下周二


@pytest.fixture(autouse=True)
def _reset():
    week_service.reset_cache()
    yield
    week_service.reset_cache()


def _stub_portal(monkeypatch, html: str):
    calls: list[int] = []
    monkeypatch.setattr(
        week_service,
        "load_cookies",
        lambda data_dir: SimpleNamespace(cookies={"PHPSESSID": "test"}, saved_at="x"),
    )
    monkeypatch.setattr(week_service, "to_httpx_cookies", lambda cookies: {})

    def fake_fetch(cookie_jar):
        calls.append(1)
        return html

    monkeypatch.setattr(week_service, "fetch_home_html", fake_fetch)
    return calls


def test_reads_portal_and_stores_it(app, session_factory, monkeypatch):
    calls = _stub_portal(monkeypatch, "<td>本学期第11周</td>")
    monkeypatch.setattr(week_service, "local_today", lambda tz: DAY1)

    with session_factory() as session:
        row = get_settings_row(session)
        value = get_current_week(app.state.config, session, row, TZ)

    assert value is not None
    assert value.week == 11
    assert value.week_start == date(2026, 11, 23)
    assert value.source == "portal"

    with session_factory() as session:
        row = get_settings_row(session)
        assert row.portal_week == 11
        assert row.portal_week_checked_on == DAY1

    with session_factory() as session:
        row = get_settings_row(session)
        again = get_current_week(app.state.config, session, row, TZ)

    assert again is not None
    assert again.week == 11
    assert len(calls) == 1, "同一自然周内不应重复请求教务页面"


def test_advances_one_week_when_portal_fails_next_week(
    app, session_factory, monkeypatch
):
    _stub_portal(monkeypatch, "<td>本学期第11周</td>")
    monkeypatch.setattr(week_service, "local_today", lambda tz: DAY1)
    with session_factory() as session:
        row = get_settings_row(session)
        get_current_week(app.state.config, session, row, TZ)

    calls = _stub_portal(monkeypatch, "")
    monkeypatch.setattr(week_service, "local_today", lambda tz: DAY2)
    with session_factory() as session:
        row = get_settings_row(session)
        value = get_current_week(app.state.config, session, row, TZ)
        assert value is not None
        assert value.week == 12
        assert value.source == "cached"

    # 同一天内失败后不再重复请求
    with session_factory() as session:
        row = get_settings_row(session)
        get_current_week(app.state.config, session, row, TZ)
    assert len(calls) == 1


def test_falls_back_to_term_start_without_any_portal_value(
    app, session_factory, monkeypatch
):
    monkeypatch.setattr(week_service, "load_cookies", lambda data_dir: None)
    monkeypatch.setattr(week_service, "local_today", lambda tz: date(2026, 9, 21))

    with session_factory() as session:
        row = get_settings_row(session)
        row.term_start_date = date(2026, 9, 7)
        session.flush()
        value = get_current_week(app.state.config, session, row, TZ)

    assert value is not None
    assert value.week == 3
    assert value.source == "fallback"


def test_returns_none_when_nothing_is_known(app, session_factory, monkeypatch):
    monkeypatch.setattr(week_service, "load_cookies", lambda data_dir: None)
    monkeypatch.setattr(week_service, "local_today", lambda tz: DAY1)

    with session_factory() as session:
        row = get_settings_row(session)
        assert get_current_week(app.state.config, session, row, TZ) is None
