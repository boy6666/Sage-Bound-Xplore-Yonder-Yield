from __future__ import annotations

from pathlib import Path

from student_workbench.adapters.chaoxing_parser import parse_all_task

FIXTURE = (Path(__file__).parent / "fixtures" / "chaoxing_all_task.html").read_text(
    encoding="utf-8"
)


def test_parses_title_status_and_course():
    works = parse_all_task(FIXTURE)

    assert len(works) == 3
    first = works[0]
    assert first.work_id == "50001"
    assert first.title == "示例作业一：面向对象练习"
    assert first.status == "未提交"
    assert first.course_id == "1001"
    assert first.class_id == "2001"
    assert first.course_name == "示例课程A"
    assert first.task_url.startswith("https://mooc1-api.chaoxing.com/mooc-ans/mooc2/work/task?")
    assert "workId=50001" in first.task_url


def test_status_maps_to_done_flag():
    works = {work.work_id: work for work in parse_all_task(FIXTURE)}

    assert works["50001"].done is False  # 未提交
    assert works["50002"].done is True  # 待批阅 = 已提交
    assert works["50003"].done is True  # 已完成


def test_entry_without_task_url_is_skipped():
    works = parse_all_task(FIXTURE)
    assert all(work.work_id for work in works)
    assert "没有链接的条目" not in [work.title for work in works]


def test_empty_page_returns_empty_list():
    assert parse_all_task("<html><body>没有作业</body></html>") == []