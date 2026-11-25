"""Read a project's GitHub state with the token stored in the OS keyring.

Only read-only endpoints are used: repository info, open pull requests, open
issues and the latest workflow runs. The token never leaves the process and is
never written to the database.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

API_BASE = "https://api.github.com"
_SSH_PATTERN = re.compile(r"^git@github\.com:([^/]+)/(.+?)(?:\.git)?$")


def parse_github_remote(url: str | None) -> tuple[str, str] | None:
    """Return ``(owner, repo)`` for a GitHub remote URL, else ``None``."""
    if not url:
        return None
    text = url.strip()
    match = _SSH_PATTERN.match(text)
    if match:
        return match.group(1), match.group(2)

    parts = urlsplit(text)
    if parts.hostname != "github.com":
        return None
    path = parts.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2:
        return None
    return segments[0], segments[1]


def _get(client: httpx.Client, path: str, token: str | None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "student-workbench",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.get(f"{API_BASE}{path}", headers=headers)
    response.raise_for_status()
    return response.json()


def _age_days(value: str | None, now: datetime) -> int | None:
    if not value:
        return None
    try:
        created = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, (now - created).days)


def fetch_github_state(
    owner: str,
    repo: str,
    token: str | None = None,
    *,
    timeout: float = 20.0,
) -> dict:
    now = datetime.now(UTC)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        repo_data = _get(client, f"/repos/{owner}/{repo}", token)
        pulls = _get(
            client, f"/repos/{owner}/{repo}/pulls?state=open&per_page=50", token
        )
        issues = _get(
            client, f"/repos/{owner}/{repo}/issues?state=open&per_page=50", token
        )
        runs = _get(
            client, f"/repos/{owner}/{repo}/actions/runs?per_page=10", token
        )

    real_issues = [item for item in issues if "pull_request" not in item]
    ages = [_age_days(item.get("created_at"), now) for item in pulls]
    oldest_pull = max((age for age in ages if age is not None), default=None)

    ci_status = "none"
    ci_name = None
    for run in runs.get("workflow_runs", [])[:5]:
        ci_name = run.get("name")
        if run.get("status") != "completed":
            ci_status = "pending"
        elif run.get("conclusion") == "failure":
            ci_status = "failure"
        else:
            ci_status = "success"
        break

    return {
        "state": "ok",
        "error": None,
        "owner": owner,
        "repo": repo,
        "private": bool(repo_data.get("private")),
        "default_branch": repo_data.get("default_branch"),
        "open_issues": len(real_issues),
        "open_pulls": len(pulls),
        "oldest_pull_days": oldest_pull,
        "ci_status": ci_status,
        "ci_name": ci_name,
        "pushed_at": repo_data.get("pushed_at"),
        "fetched_at": now.isoformat(),
    }