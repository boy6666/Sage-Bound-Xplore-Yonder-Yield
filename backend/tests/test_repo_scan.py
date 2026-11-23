from __future__ import annotations

import shutil
import subprocess

import pytest

from tests.helpers import create_project

GIT = shutil.which("git")
pytestmark = pytest.mark.skipif(GIT is None, reason="git is not installed")


def git(cwd, *args):
    return subprocess.run(
        [GIT, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def init_repo(path):
    path.mkdir()
    git(path, "init")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "feat: init")
    return path


def test_scan_invalid_path_returns_422(client, tmp_path):
    project = create_project(client, name="项目")
    response = client.post(
        f"/api/v1/projects/{project['id']}/scan"
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REPO_PATH_INVALID"

    missing = tmp_path / "missing"
    response = client.patch(
        f"/api/v1/projects/{project['id']}", json={"repo_path": str(missing)}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REPO_PATH_INVALID"


def test_scan_non_git_directory_returns_422(client, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    response = client.post(
        "/api/v1/projects", json={"name": "非仓库", "repo_path": str(plain)}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REPO_PATH_INVALID"


def test_scan_reports_branch_and_counts(client, tmp_path):
    repo = init_repo(tmp_path / "repo")
    project = create_project(client, name="仓库", repo_path=str(repo))

    response = client.post(f"/api/v1/projects/{project['id']}/scan")
    assert response.status_code == 200, response.text
    body = response.json()
    snapshot = body["snapshot"]
    assert snapshot["state"] == "ok"
    assert snapshot["branch"] in {"main", "master"}
    assert snapshot["upstream"] is None
    assert snapshot["ahead"] is None
    assert snapshot["behind"] is None
    assert snapshot["dirty_files"] == 0
    assert snapshot["staged_files"] == 0
    assert snapshot["untracked_files"] == 0
    assert snapshot["last_commit_subject"] == "feat: init"
    assert snapshot["last_commit_at"] is not None
    assert body["health"]["level"] == "yellow"

    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    (repo / "new.py").write_text("print(1)\n", encoding="utf-8")
    git(repo, "add", "new.py")
    (repo / "loose.txt").write_text("x\n", encoding="utf-8")

    snapshot = client.post(f"/api/v1/projects/{project['id']}/scan").json()["snapshot"]
    assert snapshot["dirty_files"] == 2
    assert snapshot["staged_files"] == 1
    assert snapshot["untracked_files"] == 1

    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    assert detail["repo_snapshot"]["dirty_files"] == 2
    actions = {reason["action"] for reason in detail["project"]["health"]["reasons"]}
    assert "repo" in actions


def test_scan_reports_ahead_and_behind_with_upstream(client, tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", str(remote))
    work = tmp_path / "work"
    git(tmp_path, "clone", str(remote), str(work))
    git(work, "checkout", "-b", "main")
    git(work, "config", "user.email", "test@example.com")
    git(work, "config", "user.name", "Test")
    (work / "a.txt").write_text("a\n", encoding="utf-8")
    git(work, "add", ".")
    git(work, "commit", "-m", "first")
    git(work, "push", "-u", "origin", "main")

    (work / "a.txt").write_text("b\n", encoding="utf-8")
    git(work, "commit", "-am", "local ahead")

    other = tmp_path / "other"
    git(tmp_path, "clone", str(remote), str(other))
    git(other, "checkout", "-B", "main", "origin/main")
    git(other, "config", "user.email", "test@example.com")
    git(other, "config", "user.name", "Test")
    (other / "b.txt").write_text("b\n", encoding="utf-8")
    git(other, "add", ".")
    git(other, "commit", "-m", "remote ahead")
    git(other, "push", "origin", "main")
    git(work, "fetch", "origin")

    project = create_project(client, name="仓库", repo_path=str(work))
    snapshot = client.post(
        f"/api/v1/projects/{project['id']}/scan"
    ).json()["snapshot"]
    assert snapshot["upstream"] == "origin/main"
    assert snapshot["ahead"] == 1
    assert snapshot["behind"] == 1


def test_scan_failure_stores_error_snapshot(client, tmp_path):
    repo = init_repo(tmp_path / "repo")
    project = create_project(client, name="仓库", repo_path=str(repo))
    client.patch(
        f"/api/v1/projects/{project['id']}", json={"next_action": "继续推进"}
    )
    assert client.post(f"/api/v1/projects/{project['id']}/scan").status_code == 200

    (repo / ".git").rename(repo / "git-moved-away")

    response = client.post(f"/api/v1/projects/{project['id']}/scan")
    assert response.status_code == 200, response.text
    snapshot = response.json()["snapshot"]
    assert snapshot["state"] == "error"
    assert snapshot["error"]
    assert response.json()["health"]["level"] == "unknown"

    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    assert detail["repo_snapshot"]["state"] == "error"
    assert detail["project"]["health"]["level"] == "unknown"
