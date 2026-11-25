from __future__ import annotations

from datetime import UTC, date, datetime

from student_workbench.services.health import HealthInputs, compute_health
from student_workbench.timeutil import get_tz

TZ = get_tz("Asia/Shanghai")
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def _inputs(**overrides) -> HealthInputs:
    base = dict(
        status="in_progress",
        status_reason=None,
        status_changed_at=NOW,
        resume_at=None,
        next_action="继续写解析器",
        next_action_updated_at=NOW,
        milestones=(),
        repo_path=None,
        snapshot=None,
        now=NOW,
        today=date(2026, 11, 25),
        stale_hours=72,
        inactive_days=14,
        tz=TZ,
    )
    base.update(overrides)
    return HealthInputs(**base)


def test_ci_failure_turns_health_red():
    health = compute_health(
        _inputs(
            github={
                "state": "ok",
                "ci_status": "failure",
                "ci_name": "tests",
                "oldest_pull_days": None,
            }
        )
    )

    assert health["level"] == "red"
    assert any(reason["code"] == "CI_FAILING" for reason in health["reasons"])


def test_stale_pull_request_turns_health_yellow():
    health = compute_health(
        _inputs(
            github={
                "state": "ok",
                "ci_status": "success",
                "oldest_pull_days": 12,
                "open_pulls": 3,
            }
        )
    )

    assert health["level"] == "yellow"
    assert any(
        reason["code"] == "STALE_PULL_REQUEST" for reason in health["reasons"]
    )


def test_github_unreachable_is_unknown_not_red():
    health = compute_health(
        _inputs(github={"state": "error", "error": "令牌无效"})
    )

    assert health["level"] == "unknown"
    assert any(
        reason["code"] == "GITHUB_UNREACHABLE" for reason in health["reasons"]
    )


def test_healthy_github_does_not_add_noise():
    health = compute_health(
        _inputs(
            github={
                "state": "ok",
                "ci_status": "success",
                "oldest_pull_days": 2,
                "open_pulls": 1,
            }
        )
    )

    assert health["level"] == "green"
    assert health["reasons"] == []


def test_recent_pull_is_not_flagged():
    health = compute_health(
        _inputs(
            github={
                "state": "ok",
                "ci_status": "none",
                "oldest_pull_days": 3,
                "open_pulls": 1,
            }
        )
    )

    assert health["level"] == "green"