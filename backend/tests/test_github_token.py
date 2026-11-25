from __future__ import annotations

from student_workbench.services import credentials


def test_settings_expose_only_token_presence(client, monkeypatch):
    monkeypatch.setattr(credentials, "load_github_token", lambda: "ghp_secret")

    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["github_token_saved"] is True
    assert "ghp_secret" not in response.text


def test_save_github_token(client, monkeypatch):
    saved: list[str] = []
    monkeypatch.setattr(
        credentials, "save_github_token", lambda token: saved.append(token) or True
    )

    response = client.put(
        "/api/v1/settings/github-token", json={"token": "ghp_abc123"}
    )

    assert response.status_code == 200
    assert response.json() == {"saved": True}
    assert saved == ["ghp_abc123"]


def test_save_github_token_reports_store_failure(client, monkeypatch):
    monkeypatch.setattr(credentials, "save_github_token", lambda token: False)

    response = client.put(
        "/api/v1/settings/github-token", json={"token": "ghp_abc123"}
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "CREDENTIAL_STORE_FAILED"


def test_delete_github_token(client, monkeypatch):
    called: list[int] = []
    monkeypatch.setattr(
        credentials, "delete_github_token", lambda: called.append(1) or True
    )

    response = client.delete("/api/v1/settings/github-token")

    assert response.status_code == 204
    assert called == [1]