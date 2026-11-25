from __future__ import annotations


def _create(client, path: str, name: str = "FL 联邦学习") -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "status": "planning", "repo_path": path},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_directory_without_git_can_be_used(client, tmp_path):
    target = tmp_path / "2026FL"
    target.mkdir()

    project = _create(client, str(target))

    assert project["repo_path"] == str(target)


def test_missing_directory_is_still_rejected(client, tmp_path):
    response = client.post(
        "/api/v1/projects",
        json={"name": "X", "repo_path": str(tmp_path / "nope")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REPO_PATH_INVALID"


def test_scan_without_git_reports_no_git(client, tmp_path):
    target = tmp_path / "2026FL"
    target.mkdir()
    project = _create(client, str(target))

    response = client.post(f"/api/v1/projects/{project['id']}/scan")

    assert response.status_code == 200
    data = response.json()
    assert data["snapshot"]["state"] == "no_git"
    assert data["snapshot"]["error"] is None
    codes = [reason["code"] for reason in data["health"]["reasons"]]
    assert "REPO_NOT_GIT" in codes