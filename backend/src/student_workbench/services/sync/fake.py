from __future__ import annotations

ACADEMIC_COURSES = [
    {
        "external_id": "c-1",
        "name": "操作系统",
        "term": "2026-2027-1",
        "teacher": "张老师",
        "source_url": "https://academic.example.edu/course/c-1",
    },
    {
        "external_id": "c-2",
        "name": "数据库原理",
        "term": "2026-2027-1",
        "teacher": "李老师",
        "source_url": "https://academic.example.edu/course/c-2",
    },
]

ACADEMIC_SCHEDULE = {
    "c-1": [
        {
            "external_id": "s-1",
            "weekday": 1,
            "start_time": "08:00",
            "end_time": "09:40",
            "location": "教三-201",
            "start_week": 1,
            "end_week": 16,
            "pattern": "all",
        }
    ],
    "c-2": [
        {
            "external_id": "s-2",
            "weekday": 3,
            "start_time": "10:00",
            "end_time": "11:40",
            "location": "教二-105",
            "start_week": 1,
            "end_week": 16,
            "pattern": "all",
        }
    ],
}

LEARNING_COURSES = [
    {
        "external_id": "lc-1",
        "name": "操作系统",
        "term": "2026-2027-1",
        "teacher": "张老师",
        "source_url": "https://learning.example.edu/course/lc-1",
    },
    {
        "external_id": "lc-2",
        "name": "数据库原理",
        "term": "2026-2027-1",
        "teacher": "李老师",
        "source_url": "https://learning.example.edu/course/lc-2",
    },
]

LEARNING_ASSIGNMENTS = [
    {
        "external_id": "hw-1001",
        "course_external_id": "lc-1",
        "title": "操作系统实验二",
        "description": "先补全页表部分",
        "due_at": "2026-11-27T23:59:00+08:00",
        "external_status": "open",
        "source_url": "https://learning.example.edu/assignment/hw-1001",
    },
    {
        "external_id": "hw-1002",
        "course_external_id": "lc-2",
        "title": "数据库习题三",
        "description": None,
        "due_at": "2026-11-25T23:59:00+08:00",
        "external_status": "submitted",
        "source_url": "https://learning.example.edu/assignment/hw-1002",
    },
    {
        "external_id": "hw-1003",
        "course_external_id": "lc-1",
        "title": "操作系统实验一",
        "description": None,
        "due_at": "2026-11-10T23:59:00+08:00",
        "external_status": "graded",
        "source_url": "https://learning.example.edu/assignment/hw-1003",
    },
    {
        "external_id": "hw-1004",
        "course_external_id": "lc-1",
        "title": "操作系统实验零",
        "description": None,
        "due_at": "2026-11-20T23:59:00+08:00",
        "external_status": "open",
        "source_url": "https://learning.example.edu/assignment/hw-1004",
    },
]


def weeks_for(start_week: int, end_week: int, pattern: str) -> list[int]:
    weeks = list(range(start_week, end_week + 1))
    if pattern == "odd":
        return [week for week in weeks if week % 2 == 1]
    if pattern == "even":
        return [week for week in weeks if week % 2 == 0]
    return weeks


def weeks_label(start_week: int, end_week: int, pattern: str) -> str:
    suffix = {"odd": " 单周", "even": " 双周"}.get(pattern, "")
    return f"{start_week}-{end_week}周{suffix}"
