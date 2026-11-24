from __future__ import annotations

from pathlib import Path

import pytest

from student_workbench.adapters.kb_parser import parse_kb_html

FIXTURE = Path(__file__).parent / "fixtures" / "academic_kb_sample.html"


@pytest.fixture(scope="module")
def parsed():
    return parse_kb_html(FIXTURE.read_text(encoding="utf-8"))


def test_reads_term_selector(parsed):
    assert parsed.term_value == "20261"
    assert parsed.term_label == "2026-2027学年第一学期"


def test_finds_every_course_once(parsed):
    names = {cell.course_name for cell in parsed.cells}
    assert names == {
        "机器学习导论",
        "云平台开发",
        "数据库系统",
        "Python应用程序设计",
        "编译原理",
        "操作系统",
        "Linux操作系统应用",
    }
    assert len(parsed.courses()) == 7


def test_weekday_mapping_survives_colspan(parsed):
    by_name = {cell.course_name: cell for cell in parsed.cells}
    # Tuesday occupies two physical columns; Thursday too.
    assert by_name["数据库系统"].weekday == 2
    assert by_name["Python应用程序设计"].weekday == 2
    assert by_name["编译原理"].weekday == 4
    assert by_name["操作系统"].weekday == 4
    assert by_name["云平台开发"].weekday == 4
    assert by_name["机器学习导论"].weekday == 1
    assert by_name["Linux操作系统应用"].weekday == 1


def test_rowspan_extends_end_time(parsed):
    by_name = {cell.course_name: cell for cell in parsed.cells}
    monday = by_name["机器学习导论"]
    assert (monday.start_time, monday.end_time) == ("08:00", "09:40")
    assert (monday.period_start, monday.period_end) == (1, 2)

    late = by_name["数据库系统"]
    assert (late.start_time, late.end_time) == ("10:00", "11:40")
    assert (late.period_start, late.period_end) == (3, 4)


def test_noon_period_is_offset(parsed):
    by_name = {cell.course_name: cell for cell in parsed.cells}
    noon = by_name["Linux操作系统应用"]
    assert (noon.start_time, noon.end_time) == ("12:30", "14:05")
    assert (noon.period_start, noon.period_end) == (101, 102)


def test_odd_even_weeks(parsed):
    by_name = {cell.course_name: cell for cell in parsed.cells}
    assert by_name["操作系统"].weeks == (1, 3, 5, 7, 9, 11, 13, 15)
    assert by_name["编译原理"].weeks == (2, 4, 6, 10, 12, 14, 16)
    assert by_name["机器学习导论"].weeks == tuple(range(1, 17))
    assert by_name["编译原理"].weeks_label == "2-6周(双周)、10-16周(双周)"


def test_splits_course_name_and_class_label(parsed):
    by_name = {cell.course_name: cell for cell in parsed.cells}
    monday = by_name["机器学习导论"]
    assert monday.class_label == "A 24软件 1班"
    assert monday.teacher == "王老师"
    assert monday.location == "主5#101"
    assert monday.external_id == "机器学习导论|A 24软件 1班"


def test_raises_when_table_missing():
    with pytest.raises(ValueError):
        parse_kb_html("<html><body><p>登录</p></body></html>")