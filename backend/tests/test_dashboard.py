from __future__ import annotations

import uuid
from datetime import UTC, datetime

from student_workbench.models import Connection, SyncRun
from tests.helpers import (
    create_connection,
    create_project,
    create_work_item,
    identity_by_name,
    login_ready,
)


def _link_academic_course(client):
    client.patch("/api/v1/settings", json={"term_start_date": "2026-09-01"})
    connection = create_connection(
        client, kind="academic", provider="academic_fake", name="教务（示例）"
    )
    login_ready(client, connection["id"], username="student", password="pw")
    sync = client.post(f"/api/v1/connections/{connection['id']}/sync")
    assert sync.status_code == 202

    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    identity = identity_by_name(client, "操作系统")["identity"]
    client.post(
        f"/api/v1/course-identities/{identity['id']}/link",
        json={"course_id": course["id"]},
    )
    return course, connection


def test_today_grouping_priority_and_dedupe(client):
    course, _ = _link_academic_course(client)

    overdue = create_work_item(
        client, title="逾期", due_at="2026-11-20T10:00:00+08:00"
    )
    planned = create_work_item(
        client,
        title="今天计划",
        due_at="2026-11-28T10:00:00+08:00",
        planned_start_at="2026-11-23T09:00:00+08:00",
    )
    planned_overdue = create_work_item(
        client,
        title="逾期但今天计划",
        due_at="2026-11-18T10:00:00+08:00",
        planned_start_at="2026-11-23T14:00:00+08:00",
    )
    upcoming = create_work_item(
        client, title="即将截止", due_at="2026-11-26T10:00:00+08:00"
    )
    blocked = create_work_item(client, title="受阻", blocked_reason="等资料")
    overdue_blocked = create_work_item(
        client,
        title="逾期又受阻",
        due_at="2026-11-19T10:00:00+08:00",
        blocked_reason="等资料",
    )
    create_work_item(client, title="已忽略", status="dismissed")
    create_work_item(client, title="已完成", status="done")
    create_work_item(client, title="太远", due_at="2026-12-10T10:00:00+08:00")

    response = client.get("/api/v1/dashboard/today", params={"date": "2026-11-23"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "date",
        "timezone",
        "classes_today",
        "overdue",
        "today_planned",
        "upcoming_unplanned",
        "blocked",
        "project_risks",
        "data_warnings",
    }
    assert body["date"] == "2026-11-23"
    assert body["timezone"] == "Asia/Shanghai"

    def ids(key):
        return {item["id"] for item in body[key]}

    assert ids("overdue") == {overdue["id"], overdue_blocked["id"]}
    assert ids("today_planned") == {planned["id"], planned_overdue["id"]}
    assert ids("upcoming_unplanned") == {upcoming["id"]}
    assert ids("blocked") == {blocked["id"]}

    seen = []
    for key in ("overdue", "today_planned", "upcoming_unplanned", "blocked"):
        seen.extend(item["id"] for item in body[key])
    assert len(seen) == len(set(seen))

    assert len(body["classes_today"]) == 1
    klass = body["classes_today"][0]
    assert klass["course_id"] == course["id"]
    assert klass["course_name"] == "操作系统"
    assert klass["start_time"] == "08:00"
    assert klass["end_time"] == "09:40"
    assert klass["location"] == "教三-201"
    assert klass["open_todos"] == 0

    tuesday = client.get(
        "/api/v1/dashboard/today", params={"date": "2026-11-24"}
    ).json()
    assert tuesday["classes_today"] == []


def test_today_missing_term_start_does_not_guess(client):
    connection = create_connection(
        client, kind="academic", provider="academic_fake", name="教务（示例）"
    )
    login_ready(client, connection["id"], username="student", password="pw")
    assert client.post(f"/api/v1/connections/{connection['id']}/sync").status_code == 202
    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    identity = identity_by_name(client, "操作系统")["identity"]
    client.post(
        f"/api/v1/course-identities/{identity['id']}/link",
        json={"course_id": course["id"]},
    )

    body = client.get("/api/v1/dashboard/today", params={"date": "2026-11-23"}).json()
    assert body["classes_today"] == []
    assert any("学期" in warning for warning in body["data_warnings"])


def test_today_project_risks_and_data_warnings(client, session_factory):
    project = create_project(client, name="个人工作台")
    client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "blocked", "status_reason": "等助教回复"},
    )
    healthy = create_project(client, name="健康项目")
    client.patch(
        f"/api/v1/projects/{healthy['id']}", json={"next_action": "继续推进"}
    )

    connection = create_connection(
        client, kind="learning", provider="learning_fake", name="学习通（示例）"
    )
    with session_factory() as session:
        row = session.get(Connection, connection["id"])
        row.status = "error"
        session.add(
            SyncRun(
                id=str(uuid.uuid4()),
                connection_id=connection["id"],
                status="failed",
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                counts_json={"courses": 0, "items": 0, "schedule": 0},
                error_code="PLATFORM_STRUCTURE_CHANGED",
                error_message="页面结构变化",
            )
        )
        session.commit()

    body = client.get("/api/v1/dashboard/today", params={"date": "2026-11-23"}).json()
    assert [risk["project_id"] for risk in body["project_risks"]] == [project["id"]]
    assert body["project_risks"][0]["level"] == "red"
    assert body["project_risks"][0]["reason"] == "项目受阻：等助教回复"
    assert "学习通（示例）最近一次同步失败" in body["data_warnings"]
