from __future__ import annotations

import pytest

from student_workbench.adapters import academic_http


def test_refusal_page_counts_as_expired_session(monkeypatch):
    monkeypatch.setattr(
        academic_http,
        "_fetch",
        lambda *args, **kwargs: "<html><title>拒绝访问该页面 (403)</title></html>",
    )
    assert academic_http.fetch_schedule_html({}) == ""


def test_login_page_counts_as_expired_session(monkeypatch):
    monkeypatch.setattr(
        academic_http,
        "_fetch",
        lambda *args, **kwargs: '<html><a id="loginbtn">登录</a></html>',
    )
    assert academic_http.fetch_schedule_html({}) == ""


def test_unknown_page_raises_structure_changed(monkeypatch):
    monkeypatch.setattr(
        academic_http, "_fetch", lambda *args, **kwargs: "<html><body>hello</body></html>"
    )
    with pytest.raises(academic_http.ScheduleStructureChanged):
        academic_http.fetch_schedule_html({})


def test_timetable_page_is_returned(monkeypatch):
    monkeypatch.setattr(
        academic_http,
        "_fetch",
        lambda *args, **kwargs: '<table class="data small solid"></table>',
    )
    assert academic_http.fetch_schedule_html({}) != ""


def test_adjustments_refusal_page_is_empty(monkeypatch):
    monkeypatch.setattr(
        academic_http,
        "_fetch",
        lambda *args, **kwargs: "<html>拒绝访问该页面</html>",
    )
    assert academic_http.fetch_adjustments_html({}) == ""