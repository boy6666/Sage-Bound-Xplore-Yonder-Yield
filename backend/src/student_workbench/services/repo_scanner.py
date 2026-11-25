from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from ..errors import AppError

GIT_TIMEOUT_SECONDS = 15
SENSITIVE_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "KEY")


class ScanError(Exception):
    pass


def _git_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if any(marker in upper for marker in SENSITIVE_MARKERS):
            continue
        env[key] = value
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    return env


def _run(path: Path, args: list[str]) -> str:
    command = ["git", *args]
    try:
        result = subprocess.run(
            command,
            cwd=str(path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            env=_git_env(),
            shell=False,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ScanError(f"无法执行 git: {exc}") from exc
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        raise ScanError(message[:500] or f"git 返回码 {result.returncode}")
    return result.stdout


def _repo_path(path: str) -> Path:
    try:
        candidate = Path(path)
    except (OSError, ValueError) as exc:
        raise AppError(
            "REPO_PATH_INVALID", "仓库路径不合法", 422, {"repo_path": path}
        ) from exc
    if not candidate.is_dir():
        raise AppError(
            "REPO_PATH_INVALID", "仓库路径不存在", 422, {"repo_path": path}
        )
    return candidate


def validate_repo_path(path: str) -> Path:
    candidate = _repo_path(path)
    try:
        output = _run(candidate, ["rev-parse", "--is-inside-work-tree"])
    except ScanError as exc:
        raise AppError(
            "REPO_PATH_INVALID", "目录不是 Git 工作树", 422, {"repo_path": path}
        ) from exc
    if output.strip() != "true":
        raise AppError(
            "REPO_PATH_INVALID", "目录不是 Git 工作树", 422, {"repo_path": path}
        )
    return candidate


def ensure_scan_path(path: str) -> Path:
    return _repo_path(path)


def remote_url(path: Path) -> str | None:
    try:
        value = _run(path, ["remote", "get-url", "origin"]).strip()
    except ScanError:
        return None
    return value or None


def is_git_repo(path: Path) -> bool:
    try:
        return _run(path, ["rev-parse", "--is-inside-work-tree"]).strip() == "true"
    except ScanError:
        return False


def scan_repo(path: Path) -> dict:
    branch: str | None = None
    try:
        branch_output = _run(path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
        if branch_output and branch_output != "HEAD":
            branch = branch_output
    except ScanError:
        branch = None

    upstream: str | None = None
    ahead: int | None = None
    behind: int | None = None
    try:
        upstream_output = _run(
            path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
        ).strip()
        upstream = upstream_output or None
    except ScanError:
        upstream = None
    if upstream:
        try:
            parts = _run(
                path, ["rev-list", "--left-right", "--count", f"{upstream}...HEAD"]
            ).split()
            behind = int(parts[0])
            ahead = int(parts[1])
        except (ScanError, ValueError, IndexError):
            ahead = None
            behind = None

    dirty_files = 0
    staged_files = 0
    untracked_files = 0
    try:
        status_output = _run(path, ["status", "--porcelain=v1"])
    except ScanError as exc:
        raise ScanError(str(exc)) from exc
    for line in status_output.splitlines():
        if not line.strip():
            continue
        if line.startswith("??"):
            untracked_files += 1
            continue
        dirty_files += 1
        if line[0] not in (" ", "?"):
            staged_files += 1

    last_commit_at: datetime | None = None
    last_commit_subject: str | None = None
    try:
        log_output = _run(path, ["log", "-1", "--format=%cI%x1f%s"]).strip()
        if log_output:
            committed, _, subject = log_output.partition("\x1f")
            last_commit_at = datetime.fromisoformat(committed.strip())
            last_commit_subject = subject.strip() or None
    except (ScanError, ValueError):
        last_commit_at = None
        last_commit_subject = None

    return {
        "state": "ok",
        "error": None,
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "dirty_files": dirty_files,
        "staged_files": staged_files,
        "untracked_files": untracked_files,
        "last_commit_at": last_commit_at,
        "last_commit_subject": last_commit_subject,
    }
