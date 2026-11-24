from __future__ import annotations

import uuid
from datetime import UTC, datetime

from student_workbench.models import SyncRun
from tests.helpers import create_connection, login_ready


def test_create_and_list_connections(client):
    connection = create_connection(client)
    assert connection["kind"] == "learning"
    assert connection["provider"] == "learning_fake"
    assert connection["status"] == "unconfigured"
    assert connection["account_label"] is None
    assert connection["credential_saved"] is False

    items = client.get("/api/v1/connections").json()["items"]
    assert [item["id"] for item in items] == [connection["id"]]


def test_invalid_provider_rejected(client):
    response = client.post(
        "/api/v1/connections",
        json={"kind": "learning", "provider": "nope", "display_name": "X"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_then_sync_is_idempotent(client):
    connection = create_connection(client)
    login = login_ready(client, connection["id"], username="demo", password="pw")
    assert login == {"status": "ready"}

    listed = client.get("/api/v1/connections").json()["items"][0]
    assert listed["status"] == "ready"
    assert listed["account_label"] == "demo"

    first = client.post(f"/api/v1/connections/{connection['id']}/sync")
    assert first.status_code == 202
    run_id = first.json()["sync_run_id"]
    run = client.get(f"/api/v1/sync-runs/{run_id}").json()
    assert run["status"] == "succeeded"
    assert run["counts"] == {"courses": 2, "items": 4, "schedule": 0, "adjustments": 0}
    assert run["connection_name"] == "学习通（示例）"
    assert run["kind"] == "learning"

    first_count = len(client.get("/api/v1/work-items").json()["items"])
    assert first_count == 4

    second = client.post(f"/api/v1/connections/{connection['id']}/sync")
    assert second.status_code == 202
    assert second.json()["sync_run_id"] != run_id
    second_run = client.get(f"/api/v1/sync-runs/{second.json()['sync_run_id']}").json()
    assert second_run["counts"] == {"courses": 2, "items": 4, "schedule": 0, "adjustments": 0}
    assert len(client.get("/api/v1/work-items").json()["items"]) == 4

    runs = client.get("/api/v1/sync-runs", params={"limit": 20}).json()["items"]
    assert len(runs) == 2


def test_sync_requires_login(client):
    connection = create_connection(client)
    response = client.post(f"/api/v1/connections/{connection['id']}/sync")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PLATFORM_AUTH_REQUIRED"


def test_academic_fake_sync_counts(client):
    connection = create_connection(
        client, kind="academic", provider="academic_fake", name="教务（示例）"
    )
    login_ready(client, connection["id"], username="student", password="pw")
    run_id = client.post(f"/api/v1/connections/{connection['id']}/sync").json()[
        "sync_run_id"
    ]
    run = client.get(f"/api/v1/sync-runs/{run_id}").json()
    assert run["counts"] == {"courses": 2, "items": 0, "schedule": 2, "adjustments": 0}
    assert client.get("/api/v1/work-items").json()["items"] == []


def test_challenge_flow(client):
    connection = create_connection(client)
    login = client.post(
        f"/api/v1/connections/{connection['id']}/login",
        json={"username": "challenge-user", "password": "pw", "save_password": False},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["status"] == "challenge"
    challenge = body["challenge"]
    assert challenge["id"]
    assert challenge["prompt"]

    wrong = client.post(
        f"/api/v1/connections/{connection['id']}/login/challenge",
        json={"challenge_id": challenge["id"], "code": "0000"},
    )
    assert wrong.status_code == 409
    assert wrong.json()["error"]["code"] == "PLATFORM_LOGIN_FAILED"

    good = client.post(
        f"/api/v1/connections/{connection['id']}/login/challenge",
        json={"challenge_id": challenge["id"], "code": "1234"},
    )
    assert good.status_code == 200
    assert good.json() == {"status": "ready"}

    assert client.post(f"/api/v1/connections/{connection['id']}/sync").status_code == 202


def test_chaoxing_sync_requires_login(client):
    connection = create_connection(
        client, kind="learning", provider="chaoxing_v1", name="学习通"
    )
    login = client.post(
        f"/api/v1/connections/{connection['id']}/login",
        json={"username": "demo", "password": "pw", "save_password": False},
    )
    assert login.status_code == 409
    assert login.json()["error"]["code"] == "PLATFORM_NOT_CONFIGURED"

    sync = client.post(f"/api/v1/connections/{connection['id']}/sync")
    assert sync.status_code == 409
    assert sync.json()["error"]["code"] == "PLATFORM_AUTH_REQUIRED"


def test_existing_running_sync_returns_same_run(client, session_factory):
    connection = create_connection(client)
    login_ready(client, connection["id"], username="demo", password="pw")

    running_id = str(uuid.uuid4())
    with session_factory() as session:
        session.add(
            SyncRun(
                id=running_id,
                connection_id=connection["id"],
                status="running",
                started_at=datetime.now(UTC),
                counts_json={"courses": 0, "items": 0, "schedule": 0},
            )
        )
        session.commit()

    response = client.post(f"/api/v1/connections/{connection['id']}/sync")
    assert response.status_code == 202
    assert response.json()["sync_run_id"] == running_id

    runs = client.get("/api/v1/sync-runs").json()["items"]
    assert len(runs) == 1


def test_delete_connection_keeps_work_items(client):
    connection = create_connection(client)
    login_ready(client, connection["id"], username="demo", password="pw")
    assert client.post(f"/api/v1/connections/{connection['id']}/sync").status_code == 202

    assert client.delete(f"/api/v1/connections/{connection['id']}").status_code == 204
    assert client.get("/api/v1/connections").json()["items"] == []
    assert len(client.get("/api/v1/work-items").json()["items"]) == 4
