from __future__ import annotations


def test_paused_project_requires_a_reason(client):
    response = client.post(
        "/api/v1/projects", json={"name": "小语", "status": "on_hold"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROJECT_STATUS_REASON_REQUIRED"


def test_paused_project_can_be_created_with_reason(client):
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "小语",
            "description": "个人项目",
            "status": "on_hold",
            "status_reason": "目前没有精力继续",
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "on_hold"
    assert data["status_reason"] == "目前没有精力继续"

    detail = client.get(f"/api/v1/projects/{data['id']}").json()
    assert detail["status_history"][0]["reason"] == "目前没有精力继续"


def test_reason_is_optional_for_normal_statuses(client):
    response = client.post(
        "/api/v1/projects", json={"name": "正常项目", "status": "planning"}
    )

    assert response.status_code == 201
    assert response.json()["status_reason"] is None


def test_blank_reason_is_rejected(client):
    response = client.post(
        "/api/v1/projects",
        json={"name": "小语", "status": "on_hold", "status_reason": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROJECT_STATUS_REASON_REQUIRED"