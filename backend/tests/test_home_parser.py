from __future__ import annotations

from student_workbench.adapters.home_parser import parse_current_week


def test_parses_week_from_portal_home():
    html = (
        '<div id="xl"><p id="xiaoli"><table><tr align="center">'
        "<td>本学期第11周</td></tr></table></p></div>"
    )
    assert parse_current_week(html) == 11


def test_parses_week_with_spaces():
    assert parse_current_week("<td>本学期第 3 周</td>") == 3


def test_returns_none_when_week_is_absent():
    assert parse_current_week("<html><body>没有周次</body></html>") is None


def test_ignores_unrelated_week_text():
    assert parse_current_week("<td>第3周作业</td>") is None
