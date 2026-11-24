from __future__ import annotations

from pathlib import Path

import pytest

from student_workbench.adapters.adjustments_parser import (
    KIND_CANCEL,
    KIND_MAKEUP,
    KIND_MOVE,
    parse_adjustments_html,
)

FIXTURE = Path(__file__).parent / "fixtures" / "academic_adjustments_sample.html"

EMPTY_PAGE = """
<html><body>
<h3>调停补课信息 - 2026-2027学年第一学期</h3>
<table class="data small" id="data_table">
  <thead><tr><th>序号</th><th>类型</th><th>课程班名称</th><th>教师</th>
  <th>调/停课周</th><th>星期</th><th>节次</th><th>调/停课日期</th><th>教室</th></tr></thead>
  <tbody><tr class=" even"><td colspan="10" class="left">当前没有记录</td></tr></tbody>
</table>
<table class="data small" id="data_table2">
  <thead><tr><th>序号</th><th>类型</th><th>课程班名称</th><th>教师</th>
  <th>补课周</th><th>星期</th><th>节次</th><th>补课日期</th><th>教室</th></tr></thead>
  <tbody><tr class=" even"><td colspan="10" class="left">当前没有记录</td></tr></tbody>
</table>
</body></html>
"""


@pytest.fixture(scope="module")
def parsed():
    return parse_adjustments_html(FIXTURE.read_text(encoding="utf-8"))


def test_reads_term_from_heading(parsed):
    assert parsed.term_label == "2026-2027学年第一学期"


def test_parses_all_records(parsed):
    assert len(parsed.records) == 3
    kinds = [record.kind for record in parsed.records]
    assert kinds == [KIND_MOVE, KIND_CANCEL, KIND_MAKEUP]


def test_cancel_record_fields(parsed):
    cancel = next(r for r in parsed.records if r.kind == KIND_CANCEL)
    assert cancel.course_name == "软件质量与测试"
    assert cancel.class_label == "A 24软件 1班"
    assert cancel.teacher == "辜萍萍"
    assert cancel.week == 12
    assert cancel.weekday == 4
    assert (cancel.period_start, cancel.period_end) == (3, 4)
    assert cancel.date == "2026-11-26"
    assert cancel.room == "主5#506"


def test_move_record_fields(parsed):
    move = next(r for r in parsed.records if r.kind == KIND_MOVE)
    assert move.course_name == "操作系统"
    assert move.weekday == 3
    assert (move.period_start, move.period_end) == (5, 6)


def test_makeup_record_fields(parsed):
    makeup = next(r for r in parsed.records if r.kind == KIND_MAKEUP)
    assert makeup.course_name == "操作系统"
    assert makeup.week == 13
    assert makeup.weekday == 6
    assert makeup.date == "2026-12-05"


def test_external_id_is_stable(parsed):
    first = parse_adjustments_html(FIXTURE.read_text(encoding="utf-8"))
    assert [r.external_id for r in parsed.records] == [r.external_id for r in first.records]
    assert len({r.external_id for r in parsed.records}) == 3


def test_empty_tables_are_a_definite_empty_list():
    parsed = parse_adjustments_html(EMPTY_PAGE)
    assert parsed.term_label == "2026-2027学年第一学期"
    assert parsed.records == ()


def test_missing_tables_raise():
    with pytest.raises(ValueError):
        parse_adjustments_html("<html><body><p>不是这个页面</p></body></html>")