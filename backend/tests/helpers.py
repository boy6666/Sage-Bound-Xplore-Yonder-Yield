from __future__ import annotations


def create_work_item(client, **payload):
    payload.setdefault("title", "事项")
    response = client.post("/api/v1/work-items", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_project(client, **payload):
    payload.setdefault("name", "项目")
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_connection(client, kind="learning", provider="learning_fake", name="学习通（示例）"):
    response = client.post(
        "/api/v1/connections",
        json={"kind": kind, "provider": provider, "display_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_ready(client, connection_id, username="demo", password="secret", save_password=False):
    response = client.post(
        f"/api/v1/connections/{connection_id}/login",
        json={"username": username, "password": password, "save_password": save_password},
    )
    assert response.status_code == 200, response.text
    return response.json()


def unmatched_identities(client):
    response = client.get("/api/v1/course-identities/unmatched")
    assert response.status_code == 200, response.text
    return response.json()["items"]


def identity_by_name(client, external_name):
    for entry in unmatched_identities(client):
        if entry["identity"]["external_name"] == external_name:
            return entry
    raise AssertionError(f"identity {external_name!r} not found")
