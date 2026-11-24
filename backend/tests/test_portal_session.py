from __future__ import annotations

from student_workbench.adapters.academic_http import classify
from student_workbench.adapters.portal_session import (
    clear_cookies,
    cookie_path,
    load_cookies,
    save_cookies,
    to_httpx_cookies,
)

COOKIES = [
    {"name": "PHPSESSID", "value": "abc123", "domain": "jw.xujc.com", "path": "/"},
    {"name": "route", "value": "s1", "domain": "jw.xujc.com", "path": "/"},
]


def test_save_and_load_roundtrip(tmp_path):
    path = save_cookies(tmp_path, COOKIES, "2026-11-24T10:00:00+08:00")
    assert path.exists()

    stored = load_cookies(tmp_path)
    assert stored is not None
    assert stored.saved_at == "2026-11-24T10:00:00+08:00"
    assert stored.cookies == COOKIES


def test_load_returns_none_without_file(tmp_path):
    assert load_cookies(tmp_path) is None


def test_load_ignores_corrupt_file(tmp_path):
    path = cookie_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert load_cookies(tmp_path) is None


def test_to_httpx_cookies(tmp_path):
    save_cookies(tmp_path, COOKIES, "2026-11-24T10:00:00+08:00")
    stored = load_cookies(tmp_path)
    assert to_httpx_cookies(stored.cookies) == {"PHPSESSID": "abc123", "route": "s1"}


def test_clear_cookies(tmp_path):
    save_cookies(tmp_path, COOKIES, "2026-11-24T10:00:00+08:00")
    assert clear_cookies(tmp_path) is True
    assert load_cookies(tmp_path) is None
    assert clear_cookies(tmp_path) is False


def test_classify_login_page():
    assert classify('<input type="button" id="loginbtn" value="登 录">') == "login"


def test_classify_schedule_page():
    html = '<table cellpadding="0" class="data small solid"><tr><td>课表</td></tr></table>'
    assert classify(html) == "ok"


def test_classify_unknown_page():
    assert classify("<html><body>维护中</body></html>") == "unknown"