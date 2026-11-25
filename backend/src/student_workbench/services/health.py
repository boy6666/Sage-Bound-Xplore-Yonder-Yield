from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..timeutil import ensure_utc

EVALUATED_STATUSES = ("planning", "in_progress", "blocked", "waiting")
INACTIVE_STATUSES = ("idea", "on_hold", "completed", "cancelled", "archived")


@dataclass(frozen=True)
class HealthInputs:
    status: str
    status_reason: str | None
    status_changed_at: datetime
    resume_at: datetime | None
    next_action: str | None
    next_action_updated_at: datetime | None
    milestones: Sequence[Mapping[str, Any]]
    repo_path: str | None
    snapshot: Mapping[str, Any] | None
    now: datetime
    today: date
    stale_hours: int
    inactive_days: int
    tz: ZoneInfo
    github: Mapping[str, Any] | None = None


def _reason(code: str, label: str, detail: str | None, action: str | None) -> dict:
    return {"code": code, "label": label, "detail": detail, "action": action}


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def compute_health(inputs: HealthInputs) -> dict:
    if inputs.status in INACTIVE_STATUSES:
        return {"level": "inactive", "reasons": []}

    red: list[dict] = []
    yellow: list[dict] = []
    unknown: list[dict] = []

    if inputs.status == "blocked":
        red.append(
            _reason(
                "PROJECT_BLOCKED",
                "项目受阻",
                inputs.status_reason,
                "status",
            )
        )
    elif inputs.status == "waiting":
        detail = inputs.status_reason
        if inputs.resume_at is not None:
            resume = ensure_utc(inputs.resume_at).astimezone(inputs.tz)
            suffix = f"（计划 {resume.strftime('%Y-%m-%d')} 恢复）"
            detail = f"{detail}{suffix}" if detail else suffix
        yellow.append(_reason("PROJECT_WAITING", "项目等待中", detail, "status"))

    overdue = [
        milestone
        for milestone in inputs.milestones
        if milestone.get("status") != "done"
        and _as_date(milestone.get("due_at")) is not None
        and _as_date(milestone.get("due_at")) < inputs.today
    ]
    if overdue:
        titles = "、".join(str(milestone.get("title")) for milestone in overdue[:3])
        yellow_detail = f"{titles}（共 {len(overdue)} 个）" if len(overdue) > 1 else titles
        red.append(
            _reason("MILESTONE_OVERDUE", "里程碑已逾期", yellow_detail, "milestone")
        )

    snapshot = inputs.snapshot
    if inputs.repo_path:
        if snapshot is None:
            unknown.append(
                _reason(
                    "SNAPSHOT_MISSING",
                    "仓库快照缺失",
                    "尚未成功扫描本地仓库",
                    "repo",
                )
            )
        elif snapshot.get("state") == "no_git":
            unknown.append(
                _reason(
                    "REPO_NOT_GIT",
                    "目录未纳入 Git",
                    "项目照常管理，但没有版本控制信息",
                    "repo",
                )
            )
        elif snapshot.get("state") != "ok":
            unknown.append(
                _reason(
                    "REPO_SCAN_FAILED",
                    "仓库扫描失败",
                    snapshot.get("error") or "本地 Git 扫描失败",
                    "repo",
                )
            )
        else:
            dirty = snapshot.get("dirty_files") or 0
            ahead = snapshot.get("ahead")
            behind = snapshot.get("behind")
            if dirty > 0:
                yellow.append(
                    _reason("REPO_DIRTY", "工作区有未提交修改", f"{dirty} 个文件", "repo")
                )
            if ahead:
                yellow.append(
                    _reason("REPO_UNPUSHED", "存在未推送提交", f"{ahead} 个提交", "repo")
                )
            if behind:
                yellow.append(
                    _reason("REPO_BEHIND", "本地落后远端", f"{behind} 个提交", "repo")
                )
            scanned_at = ensure_utc(snapshot.get("scanned_at"))
            if scanned_at is not None:
                age_hours = (inputs.now - scanned_at).total_seconds() / 3600
                if age_hours > inputs.stale_hours:
                    local = scanned_at.astimezone(inputs.tz).strftime("%Y-%m-%d %H:%M")
                    yellow.append(
                        _reason(
                            "SNAPSHOT_STALE",
                            "仓库快照已过期",
                            f"最近扫描于 {local}",
                            "repo",
                        )
                    )

    github = inputs.github
    if github is not None:
        if github.get("state") != "ok":
            unknown.append(
                _reason(
                    "GITHUB_UNREACHABLE",
                    "GitHub 状态不可用",
                    github.get("error") or "远端信息读取失败",
                    "github",
                )
            )
        else:
            if github.get("ci_status") == "failure":
                red.append(
                    _reason(
                        "CI_FAILING",
                        "CI 最近一次失败",
                        github.get("ci_name") or "默认分支的最新工作流",
                        "github",
                    )
                )
            stale_days = github.get("oldest_pull_days")
            if stale_days is not None and stale_days >= 7:
                yellow.append(
                    _reason(
                        "STALE_PULL_REQUEST",
                        "PR 长期未合并",
                        f"最老 {stale_days} 天，共 {github.get('open_pulls', 0)} 个开放 PR",
                        "github",
                    )
                )

    if inputs.status in ("planning", "in_progress") and not (
        inputs.next_action or ""
    ).strip():
        yellow.append(
            _reason(
                "NEXT_ACTION_MISSING",
                "缺少下一步行动",
                "补充一个可立即执行的动作",
                "next_action",
            )
        )

    if inputs.status in ("planning", "in_progress"):
        activity_candidates = [ensure_utc(inputs.status_changed_at)]
        if inputs.next_action_updated_at is not None:
            activity_candidates.append(ensure_utc(inputs.next_action_updated_at))
        if snapshot is not None and snapshot.get("state") == "ok":
            scanned_at = ensure_utc(snapshot.get("scanned_at"))
            if scanned_at is not None:
                activity_candidates.append(scanned_at)
        last_activity = max(activity_candidates)
        idle_days = (inputs.now - last_activity).total_seconds() / 86400
        if idle_days > inputs.inactive_days:
            yellow.append(
                _reason(
                    "PROJECT_INACTIVE",
                    "项目最近无活动",
                    f"{int(idle_days)} 天无更新",
                    "status",
                )
            )

    if red:
        level = "red"
    elif yellow:
        level = "yellow"
    elif unknown:
        level = "unknown"
    else:
        level = "green"

    return {"level": level, "reasons": red + yellow + unknown}
