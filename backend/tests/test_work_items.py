from __future__ import annotations

from tests.helpers import create_work_item


def test_create_work_item_defaults(client):
    item = create_work_item(client, title="操作系统实验二")
    assert item["status"] == "inbox"
    assert item["priority"] == "normal"
    assert item["item_type"] == "task"
    assert item["source_type"] == "manual"
    assert item["needs_review"] is False
    assert item["due_at"] is None
    assert item["created_at"] and item["updated_at"]


def test_create_work_item_with_schedule_roundtrips_offset(client):
    item = create_work_item(
        client,
        title="实验报告",
        notes="先补全页表部分",
        item_type="assignment",
        priority="high",
        status="planned",
        due_at="2026-11-27T23:59:00+08:00",
        planned_start_at="2026-11-24T09:00:00+08:00",
        planned_end_at="2026-11-24T11:00:00+08:00",
        estimate_minutes=90,
        blocked_reason=None,
    )
    assert item["due_at"] == "2026-11-27T23:59:00+08:00"
    assert item["planned_start_at"] == "2026-11-24T09:00:00+08:00"
    assert item["planned_end_at"] == "2026-11-24T11:00:00+08:00"
    assert item["estimate_minutes"] == 90
    assert item["notes"] == "先补全页表部分"
    assert item["item_type"] == "assignment"
    assert item["priority"] == "high"


def test_get_work_item(client):
    item = create_work_item(client, title="单独查看")
    response = client.get(f"/api/v1/work-items/{item['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "单独查看"


def test_list_work_items_filters(client):
    first = create_work_item(client, title="课程作业", status="inbox")
    create_work_item(client, title="计划中", status="planned")
    create_work_item(client, title="已完成", status="done")

    only_inbox = client.get("/api/v1/work-items", params={"status": "inbox"}).json()
    assert [item["id"] for item in only_inbox["items"]] == [first["id"]]

    searched = client.get("/api/v1/work-items", params={"q": "计划"}).json()
    assert [item["title"] for item in searched["items"]] == ["计划中"]

    limited = client.get("/api/v1/work-items", params={"limit": 1}).json()
    assert len(limited["items"]) == 1


def test_patch_status_done_sets_completed_at_then_clears(client, session_factory):
    from student_workbench.models import WorkItem

    item = create_work_item(client, title="任务", status="in_progress")
    done = client.patch(f"/api/v1/work-items/{item['id']}", json={"status": "done"})
    assert done.status_code == 200, done.text

    with session_factory() as session:
        assert session.get(WorkItem, item["id"]).completed_at is not None

    back = client.patch(f"/api/v1/work-items/{item['id']}", json={"status": "in_progress"})
    assert back.status_code == 200
    with session_factory() as session:
        assert session.get(WorkItem, item["id"]).completed_at is None


def test_dismissed_item_cannot_be_reactivated(client):
    item = create_work_item(client, title="忽略我")
    assert (
        client.patch(f"/api/v1/work-items/{item['id']}", json={"status": "dismissed"}).status_code
        == 200
    )
    response = client.patch(f"/api/v1/work-items/{item['id']}", json={"status": "inbox"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "WORK_ITEM_INVALID_TRANSITION"


def test_blocked_reason_marks_item_without_blocked_status(client):
    item = create_work_item(client, title="受阻任务")
    blocked = client.patch(
        f"/api/v1/work-items/{item['id']}",
        json={"blocked_reason": "等资料"},
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["blocked_reason"] == "等资料"
    assert blocked.json()["status"] == "inbox"

    invalid = client.patch(
        f"/api/v1/work-items/{item['id']}", json={"status": "blocked"}
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_requires_title(client):
    response = client.post("/api/v1/work-items", json={"notes": "没有标题"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_status_value_is_validation_error(client):
    item = create_work_item(client, title="任务")
    response = client.patch(f"/api/v1/work-items/{item['id']}", json={"status": "nonsense"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_work_item(client):
    item = create_work_item(client, title="删除我")
    response = client.delete(f"/api/v1/work-items/{item['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/work-items/{item['id']}").status_code == 404


def test_work_item_with_course_and_project_names(client):
    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    project = client.post("/api/v1/projects", json={"name": "个人工作台"}).json()
    item = create_work_item(
        client, title="关联", course_id=course["id"], project_id=project["id"]
    )
    assert item["course_name"] == "操作系统"
    assert item["project_name"] == "个人工作台"
