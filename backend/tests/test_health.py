from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from student_workbench.services.health import HealthInputs, compute_health

NOW = datetime(2026, 11, 23, 4, 0, tzinfo=UTC)
TZ = ZoneInfo("Asia/Shanghai")


def inputs(**overrides) -> HealthInputs:
    base = HealthInputs(
        status="planning",
        status_reason=None,
        status_changed_at=NOW - timedelta(days=1),
        resume_at=None,
        next_action="完成今日页聚合",
        next_action_updated_at=NOW - timedelta(days=1),
        milestones=(),
        repo_path=None,
        snapshot=None,
        now=NOW,
        today=date(2026, 11, 23),
        stale_hours=72,
        inactive_days=14,
        tz=TZ,
    )
    return replace(base, **overrides)


def codes(health):
    return [reason["code"] for reason in health["reasons"]]


def test_green_when_healthy_without_repo():
    health = compute_health(inputs())
    assert health == {"level": "green", "reasons": []}


@pytest.mark.parametrize(
    "status", ["idea", "on_hold", "completed", "cancelled", "archived"]
)
def test_inactive_statuses_have_no_reasons(status):
    health = compute_health(inputs(status=status, status_reason="原因"))
    assert health == {"level": "inactive", "reasons": []}


def test_blocked_is_red_with_reason_detail():
    health = compute_health(
        inputs(status="blocked", status_reason="等助教回复环境问题")
    )
    assert health["level"] == "red"
    top = health["reasons"][0]
    assert top["code"] == "PROJECT_BLOCKED"
    assert top["label"] == "项目受阻"
    assert top["detail"] == "等助教回复环境问题"
    assert top["action"] == "status"


def test_waiting_is_yellow():
    health = compute_health(
        inputs(
            status="waiting",
            status_reason="等 review",
            resume_at=NOW + timedelta(days=2),
        )
    )
    assert health["level"] == "yellow"
    assert codes(health)[0] == "PROJECT_WAITING"


def test_missing_next_action_is_yellow():
    health = compute_health(inputs(next_action=None, next_action_updated_at=None))
    assert health["level"] == "yellow"
    assert codes(health) == ["NEXT_ACTION_MISSING"]
    assert health["reasons"][0]["action"] == "next_action"


def test_overdue_milestone_is_red():
    health = compute_health(
        inputs(
            milestones=(
                {"title": "M1", "due_at": date(2026, 11, 1), "status": "open"},
                {"title": "M2", "due_at": date(2026, 11, 2), "status": "done"},
            )
        )
    )
    assert health["level"] == "red"
    assert codes(health) == ["MILESTONE_OVERDUE"]
    assert "M1" in health["reasons"][0]["detail"]
    assert health["reasons"][0]["action"] == "milestone"


def test_dirty_repo_is_yellow():
    health = compute_health(
        inputs(
            repo_path="E:/code/workbench",
            snapshot={
                "state": "ok",
                "scanned_at": NOW - timedelta(hours=1),
                "dirty_files": 2,
                "staged_files": 0,
                "untracked_files": 0,
                "ahead": 0,
                "behind": 0,
                "error": None,
            },
        )
    )
    assert health["level"] == "yellow"
    assert codes(health) == ["REPO_DIRTY"]
    assert health["reasons"][0]["detail"] == "2 个文件"
    assert health["reasons"][0]["action"] == "repo"


def test_unpushed_and_behind_repos_are_yellow():
    health = compute_health(
        inputs(
            repo_path="E:/code/workbench",
            snapshot={
                "state": "ok",
                "scanned_at": NOW - timedelta(hours=1),
                "dirty_files": 0,
                "staged_files": 0,
                "untracked_files": 0,
                "ahead": 3,
                "behind": 2,
                "error": None,
            },
        )
    )
    assert health["level"] == "yellow"
    assert codes(health) == ["REPO_UNPUSHED", "REPO_BEHIND"]
    assert health["reasons"][0]["detail"] == "3 个提交"
    assert health["reasons"][1]["detail"] == "2 个提交"


def test_stale_snapshot_is_yellow():
    health = compute_health(
        inputs(
            repo_path="E:/code/workbench",
            snapshot={
                "state": "ok",
                "scanned_at": NOW - timedelta(hours=100),
                "dirty_files": 0,
                "staged_files": 0,
                "untracked_files": 0,
                "ahead": 0,
                "behind": 0,
                "error": None,
            },
        )
    )
    assert health["level"] == "yellow"
    assert codes(health) == ["SNAPSHOT_STALE"]
    assert health["reasons"][0]["action"] == "repo"


def test_missing_snapshot_is_unknown():
    health = compute_health(inputs(repo_path="E:/code/workbench", snapshot=None))
    assert health["level"] == "unknown"
    assert codes(health) == ["SNAPSHOT_MISSING"]
    assert health["reasons"][0]["action"] == "repo"


def test_failed_snapshot_is_unknown_with_error():
    health = compute_health(
        inputs(
            repo_path="E:/code/workbench",
            snapshot={
                "state": "error",
                "scanned_at": NOW,
                "dirty_files": None,
                "staged_files": None,
                "untracked_files": None,
                "ahead": None,
                "behind": None,
                "error": "fatal: not a git repository",
            },
        )
    )
    assert health["level"] == "unknown"
    assert codes(health) == ["REPO_SCAN_FAILED"]
    assert health["reasons"][0]["detail"] == "fatal: not a git repository"


def test_inactive_project_activity_is_yellow():
    health = compute_health(
        inputs(
            status_changed_at=NOW - timedelta(days=40),
            next_action="旧计划",
            next_action_updated_at=None,
        )
    )
    assert health["level"] == "yellow"
    assert "PROJECT_INACTIVE" in codes(health)


def test_red_beats_yellow():
    health = compute_health(
        inputs(
            status="blocked",
            status_reason="等",
            next_action=None,
            next_action_updated_at=None,
        )
    )
    assert health["level"] == "red"
    assert codes(health)[0] == "PROJECT_BLOCKED"


def test_unknown_beats_green_but_not_yellow():
    unknown_only = compute_health(inputs(repo_path="E:/code/workbench"))
    assert unknown_only["level"] == "unknown"

    with_yellow = compute_health(
        inputs(
            repo_path="E:/code/workbench",
            next_action=None,
            next_action_updated_at=None,
        )
    )
    assert with_yellow["level"] == "yellow"
