from __future__ import annotations

from student_workbench.models import Project
from tests.helpers import create_project, create_work_item


def test_create_project_defaults(client):
    project = create_project(client, name="个人工作台", description="本地优先")
    assert project["status"] == "planning"
    assert project["status_reason"] is None
    assert project["status_changed_at"] is not None
    assert project["next_action"] is None
    assert project["next_action_updated_at"] is None
    assert project["open_todos"] == 0
    assert project["milestones_total"] == 0
    assert project["milestones_done"] == 0
    assert project["health"]["level"] == "yellow"
    assert "NEXT_ACTION_MISSING" in [r["code"] for r in project["health"]["reasons"]]


def test_create_project_rejects_invalid_repo_path(client):
    response = client.post(
        "/api/v1/projects",
        json={"name": "坏路径", "repo_path": "E:/definitely/not/here"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REPO_PATH_INVALID"


def test_project_status_reason_required(client):
    project = create_project(client, name="受阻项目")
    for status in ("blocked", "waiting", "on_hold", "cancelled"):
        response = client.patch(
            f"/api/v1/projects/{project['id']}", json={"status": status}
        )
        assert response.status_code == 422, status
        assert response.json()["error"]["code"] == "PROJECT_STATUS_REASON_REQUIRED"

    blank = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "blocked", "status_reason": "   "},
    )
    assert blank.status_code == 422


def test_project_status_change_appends_history(client):
    project = create_project(client, name="项目")
    before = client.get(f"/api/v1/projects/{project['id']}").json()
    history_before = before["status_history"]
    assert [entry["to_status"] for entry in history_before] == ["planning"]

    updated = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "blocked", "status_reason": "等助教回复环境问题"},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["status"] == "blocked"
    assert body["status_reason"] == "等助教回复环境问题"
    assert body["status_changed_at"] != before["project"]["status_changed_at"]
    assert body["health"]["level"] == "red"
    assert body["health"]["reasons"][0]["code"] == "PROJECT_BLOCKED"

    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    tos = [entry["to_status"] for entry in detail["status_history"]]
    assert "blocked" in tos
    latest = detail["status_history"][0]
    assert latest["from_status"] == "planning"
    assert latest["to_status"] == "blocked"
    assert latest["reason"] == "等助教回复环境问题"


def test_project_next_action_timestamp(client):
    project = create_project(client, name="项目")
    first = client.patch(
        f"/api/v1/projects/{project['id']}", json={"next_action": "完成今日页"}
    ).json()
    assert first["next_action"] == "完成今日页"
    assert first["next_action_updated_at"] is not None

    second = client.patch(
        f"/api/v1/projects/{project['id']}", json={"description": "改说明"}
    ).json()
    assert second["next_action_updated_at"] == first["next_action_updated_at"]

    third = client.patch(
        f"/api/v1/projects/{project['id']}", json={"next_action": "写测试"}
    ).json()
    assert third["next_action_updated_at"] != first["next_action_updated_at"]


def test_project_detail_shape(client):
    project = create_project(client, name="项目")
    client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={"title": "M1", "due_at": "2026-12-01"},
    )
    create_work_item(client, title="普通事项")
    todo = client.post(
        f"/api/v1/projects/{project['id']}/todos",
        json={"title": "项目待办"},
    )
    assert todo.status_code == 201, todo.text
    todo_body = todo.json()
    assert todo_body["project_id"] == project["id"]
    assert todo_body["source_type"] == "project"
    assert todo_body["item_type"] == "task"

    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    assert set(detail) == {"project", "milestones", "status_history", "repo_snapshot", "todos"}
    assert detail["repo_snapshot"] is None
    assert len(detail["milestones"]) == 1
    assert detail["milestones"][0]["due_at"] == "2026-12-01"
    assert detail["milestones"][0]["status"] == "open"
    assert [item["title"] for item in detail["todos"]] == ["项目待办"]
    assert detail["project"]["open_todos"] == 1
    assert detail["project"]["milestones_total"] == 1
    assert detail["project"]["milestones_done"] == 0


def test_milestone_patch_done_sets_completed_at(client):
    project = create_project(client, name="项目")
    milestone = client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={"title": "M1"},
    ).json()
    response = client.patch(
        f"/api/v1/milestones/{milestone['id']}", json={"status": "done"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["completed_at"] is not None

    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    assert detail["project"]["milestones_done"] == 1


def test_project_list_filter_by_status(client):
    planning = create_project(client, name="规划")
    blocked = create_project(client, name="受阻")
    client.patch(
        f"/api/v1/projects/{blocked['id']}",
        json={"status": "blocked", "status_reason": "等"},
    )
    response = client.get("/api/v1/projects", params={"status": "blocked"})
    assert [item["id"] for item in response.json()["items"]] == [blocked["id"]]
    assert planning["id"] != blocked["id"]


def test_delete_project_nulls_todo_project_id(client):
    project = create_project(client, name="待删")
    todo = client.post(
        f"/api/v1/projects/{project['id']}/todos", json={"title": "待办"}
    ).json()
    assert client.delete(f"/api/v1/projects/{project['id']}").status_code == 204
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404
    item = client.get(f"/api/v1/work-items/{todo['id']}").json()
    assert item["project_id"] is None


def test_resume_at_roundtrip(client):
    project = create_project(client, name="等待")
    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={
            "status": "waiting",
            "status_reason": "等 review",
            "resume_at": "2026-11-30T09:00:00+08:00",
        },
    )
    assert response.status_code == 200
    assert response.json()["resume_at"] == "2026-11-30T09:00:00+08:00"
    assert response.json()["health"]["level"] == "yellow"
    assert response.json()["health"]["reasons"][0]["code"] == "PROJECT_WAITING"


def test_inactive_project_health(client, session_factory):
    project = create_project(client, name="想法", status="idea")
    assert project["health"] == {"level": "inactive", "reasons": []}

    with session_factory() as session:
        row = session.get(Project, project["id"])
        row.status = "completed"
        session.commit()

    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    assert detail["project"]["health"]["level"] == "inactive"
