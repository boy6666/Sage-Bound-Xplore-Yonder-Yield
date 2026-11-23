from __future__ import annotations


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_bootstrap_defaults(client):
    response = client.get("/api/v1/bootstrap")
    assert response.status_code == 200
    body = response.json()
    assert body["setup_completed"] is False
    assert body["timezone"] == "Asia/Shanghai"
    assert set(body["counts"]) == {"inbox", "today", "projects", "courses"}
    assert body["counts"] == {"inbox": 0, "today": 0, "projects": 0, "courses": 0}
    assert len(body["today"]) == 10


def test_bootstrap_complete(client):
    response = client.post(
        "/api/v1/bootstrap/complete",
        json={"timezone": "Asia/Shanghai", "term_start_date": "2026-09-01"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["setup_completed"] is True

    settings = client.get("/api/v1/settings").json()
    assert settings["setup_completed"] is True
    assert settings["term_start_date"] == "2026-09-01"
    assert settings["timezone"] == "Asia/Shanghai"


def test_settings_patch_is_partial(client):
    response = client.patch(
        "/api/v1/settings", json={"upcoming_days": 5, "inactive_days": 10}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["upcoming_days"] == 5
    assert body["inactive_days"] == 10
    assert body["stale_snapshot_hours"] == 72
    assert body["save_platform_password"] is False


def test_settings_invalid_timezone(client):
    response = client.patch("/api/v1/settings", json={"timezone": "Not/AZone"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_origin_guard_blocks_missing_headers(raw_client):
    response = raw_client.post("/api/v1/work-items", json={"title": "x"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_ORIGIN"


def test_origin_guard_blocks_foreign_origin(client):
    response = client.post(
        "/api/v1/work-items",
        json={"title": "x"},
        headers={"Origin": "http://evil.example.com"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_ORIGIN"


def test_origin_guard_allows_localhost_write(client):
    response = client.post(
        "/api/v1/work-items",
        json={"title": "x"},
        headers={"Origin": "http://localhost:8765"},
    )
    assert response.status_code == 201, response.text


def test_reads_do_not_require_headers(raw_client):
    assert raw_client.get("/api/v1/work-items").status_code == 200


def test_not_found_error_shape(client):
    response = client.get("/api/v1/work-items/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]
    assert "details" in body["error"]


def test_session_dependency_can_be_overridden(app, client):
    from student_workbench.db import get_session

    calls = []

    def override():
        with app.state.session_factory() as session:
            calls.append(session)
            yield session

    app.dependency_overrides[get_session] = override
    try:
        assert client.get("/api/v1/work-items").status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert calls
