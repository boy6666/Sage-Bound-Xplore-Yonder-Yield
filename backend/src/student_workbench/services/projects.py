from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import (
    Milestone,
    Project,
    ProjectStatusHistory,
    RepoSnapshot,
    WorkItem,
)
from ..schemas import MilestoneCreate, MilestoneUpdate, ProjectCreate, ProjectUpdate
from ..timeutil import (
    as_utc,
    date_str,
    ensure_utc,
    iso,
    local_today,
    utcnow,
)
from .health import HealthInputs, compute_health
from .settings import current_tz, get_settings_row
from .work_items import ACTIVE_STATUSES, open_count, serialize_item

REASON_REQUIRED_STATUSES = ("blocked", "waiting", "on_hold", "cancelled")
EVALUATED_STATUSES = ("planning", "in_progress", "blocked", "waiting")


def get_project(session: Session, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise AppError("NOT_FOUND", "项目不存在", 404, {"project_id": project_id})
    return project


def _projects(session: Session, project_id: str) -> list[Milestone]:
    return list(
        session.scalars(
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.due_at.is_(None), Milestone.due_at, Milestone.created_at)
        ).all()
    )


def latest_snapshot(session: Session, project_id: str) -> RepoSnapshot | None:
    return session.scalars(
        select(RepoSnapshot)
        .where(RepoSnapshot.project_id == project_id)
        .order_by(RepoSnapshot.scanned_at.desc(), RepoSnapshot.id)
        .limit(1)
    ).first()


def snapshot_out(row: RepoSnapshot, tz: ZoneInfo) -> dict:
    return {
        "branch": row.branch,
        "upstream": row.upstream,
        "ahead": row.ahead,
        "behind": row.behind,
        "dirty_files": row.dirty_files,
        "staged_files": row.staged_files,
        "untracked_files": row.untracked_files,
        "last_commit_at": iso(row.last_commit_at, tz),
        "last_commit_subject": row.last_commit_subject,
        "scanned_at": iso(row.scanned_at, tz),
        "state": row.state,
        "error": row.error,
        "github": json.loads(row.github_json) if row.github_json else None,
        "github_error": row.github_error,
    }


def _health_inputs(
    project: Project,
    milestones: list[Milestone],
    snapshot_row: RepoSnapshot | None,
    tz: ZoneInfo,
    settings_row,
    now: datetime,
) -> HealthInputs:
    snapshot = None
    if snapshot_row is not None:
        snapshot = {
            "state": snapshot_row.state,
            "error": snapshot_row.error,
            "dirty_files": snapshot_row.dirty_files,
            "staged_files": snapshot_row.staged_files,
            "untracked_files": snapshot_row.untracked_files,
            "ahead": snapshot_row.ahead,
            "behind": snapshot_row.behind,
            "scanned_at": ensure_utc(snapshot_row.scanned_at),
        }
    github = None
    if snapshot_row is not None:
        if snapshot_row.github_json:
            try:
                github = json.loads(snapshot_row.github_json)
            except ValueError:
                github = None
        elif snapshot_row.github_error:
            github = {"state": "error", "error": snapshot_row.github_error}
    return HealthInputs(
        status=project.status,
        status_reason=project.status_reason,
        status_changed_at=ensure_utc(project.status_changed_at) or now,
        resume_at=project.resume_at,
        next_action=project.next_action,
        next_action_updated_at=project.next_action_updated_at,
        milestones=tuple(
            {"title": item.title, "due_at": item.due_at, "status": item.status}
            for item in milestones
        ),
        repo_path=project.repo_path,
        snapshot=snapshot,
        github=github,
        now=now,
        today=local_today(tz),
        stale_hours=settings_row.stale_snapshot_hours,
        inactive_days=settings_row.inactive_days,
        tz=tz,
    )


def project_health(
    session: Session, project: Project, tz: ZoneInfo, now: datetime | None = None
) -> dict:
    if now is None:
        now = utcnow()
    settings_row = get_settings_row(session)
    milestones = _projects(session, project.id)
    snapshot_row = latest_snapshot(session, project.id)
    return compute_health(
        _health_inputs(project, milestones, snapshot_row, tz, settings_row, now)
    )


def serialize_project(
    session: Session, project: Project, tz: ZoneInfo, now: datetime | None = None
) -> dict:
    milestones = _projects(session, project.id)
    done = sum(1 for item in milestones if item.status == "done")
    health = project_health(session, project, tz, now)
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "status_reason": project.status_reason,
        "status_changed_at": iso(project.status_changed_at, tz),
        "resume_at": iso(project.resume_at, tz),
        "next_action": project.next_action,
        "next_action_updated_at": iso(project.next_action_updated_at, tz),
        "repo_path": project.repo_path,
        "open_todos": open_count(session, project_id=project.id),
        "milestones_total": len(milestones),
        "milestones_done": done,
        "health": health,
        "created_at": iso(project.created_at, tz),
        "updated_at": iso(project.updated_at, tz),
    }


def serialize_milestone(milestone: Milestone, tz: ZoneInfo) -> dict:
    return {
        "id": milestone.id,
        "title": milestone.title,
        "due_at": date_str(milestone.due_at),
        "status": milestone.status,
        "completed_at": iso(milestone.completed_at, tz),
    }


def serialize_history(entry: ProjectStatusHistory, tz: ZoneInfo) -> dict:
    return {
        "id": entry.id,
        "from_status": entry.from_status,
        "to_status": entry.to_status,
        "reason": entry.reason,
        "changed_at": iso(entry.changed_at, tz),
    }


def _append_history(
    session: Session,
    project: Project,
    from_status: str | None,
    to_status: str,
    reason: str | None,
    changed_at: datetime,
) -> None:
    session.add(
        ProjectStatusHistory(
            project_id=project.id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            changed_at=changed_at,
        )
    )


def _check_repo_path(path: str | None) -> str | None:
    """Accept any existing directory; Git is optional for a project."""
    if not path:
        return None
    candidate = path.strip()
    if not candidate:
        return None
    try:
        exists = Path(candidate).is_dir()
    except (OSError, ValueError) as exc:
        raise AppError(
            "REPO_PATH_INVALID", "仓库路径不合法", 422, {"repo_path": path}
        ) from exc
    if not exists:
        raise AppError(
            "REPO_PATH_INVALID", "目录不存在", 422, {"repo_path": path}
        )
    return candidate


def create_project(session: Session, payload: ProjectCreate) -> Project:
    status = payload.status
    repo_path = _check_repo_path(payload.repo_path)
    if status in REASON_REQUIRED_STATUSES:
        raise AppError(
            "PROJECT_STATUS_REASON_REQUIRED",
            "受阻状态必须填写原因",
            422,
            {"status": status},
        )
    now = utcnow()
    project = Project(
        name=payload.name,
        description=payload.description,
        status=status,
        status_changed_at=now,
        repo_path=repo_path,
        created_at=now,
        updated_at=now,
    )
    session.add(project)
    session.flush()
    _append_history(session, project, None, status, None, now)
    session.flush()
    return project


def update_project(session: Session, project: Project, payload: ProjectUpdate) -> Project:
    data = payload.model_dump(exclude_unset=True)
    now = utcnow()

    if "repo_path" in data:
        data["repo_path"] = _check_repo_path(data["repo_path"])
    if "resume_at" in data and data["resume_at"] is not None:
        data["resume_at"] = as_utc(data["resume_at"], current_tz(session))

    if "name" in data and not (data["name"] or "").strip():
        raise AppError("VALIDATION_ERROR", "项目名不能为空", 422, {"field": "name"})

    if "status" in data and data["status"] != project.status:
        target = data["status"]
        reason = data.get("status_reason", project.status_reason)
        if target in REASON_REQUIRED_STATUSES and not (reason or "").strip():
            raise AppError(
                "PROJECT_STATUS_REASON_REQUIRED",
                "受阻状态必须填写原因",
                422,
                {"status": target},
            )
        from_status = project.status
        project.status = target
        project.status_changed_at = now
        if target not in REASON_REQUIRED_STATUSES and "status_reason" not in data:
            project.status_reason = None
        if target not in ("waiting", "on_hold") and "resume_at" not in data:
            project.resume_at = None
        _append_history(session, project, from_status, target, reason, now)

    if "status_reason" in data and data["status_reason"] != project.status_reason:
        project.status_reason = data["status_reason"]

    if "next_action" in data and data["next_action"] != project.next_action:
        project.next_action = data["next_action"]
        project.next_action_updated_at = now

    for field in ("name", "description", "resume_at", "repo_path"):
        if field in data:
            setattr(project, field, data[field])

    project.updated_at = now
    session.flush()
    return project


def delete_project(session: Session, project: Project) -> None:
    project_id = project.id
    session.execute(
        update(WorkItem)
        .where(WorkItem.project_id == project_id)
        .values(project_id=None)
    )
    session.execute(
        delete(ProjectStatusHistory).where(
            ProjectStatusHistory.project_id == project_id
        )
    )
    session.execute(delete(Milestone).where(Milestone.project_id == project_id))
    session.execute(delete(RepoSnapshot).where(RepoSnapshot.project_id == project_id))
    session.delete(project)
    session.flush()


def project_detail(
    session: Session, project: Project, tz: ZoneInfo
) -> dict:
    now = utcnow()
    milestones = _projects(session, project.id)
    history = session.scalars(
        select(ProjectStatusHistory)
        .where(ProjectStatusHistory.project_id == project.id)
        .order_by(ProjectStatusHistory.changed_at.desc(), ProjectStatusHistory.id)
    ).all()
    snapshot_row = latest_snapshot(session, project.id)
    todos = session.scalars(
        select(WorkItem)
        .where(
            WorkItem.project_id == project.id,
            WorkItem.status.in_(ACTIVE_STATUSES),
        )
        .order_by(WorkItem.created_at, WorkItem.id)
    ).unique().all()
    return {
        "project": serialize_project(session, project, tz, now),
        "milestones": [serialize_milestone(item, tz) for item in milestones],
        "status_history": [serialize_history(item, tz) for item in history],
        "repo_snapshot": snapshot_out(snapshot_row, tz) if snapshot_row else None,
        "todos": [serialize_item(item, tz) for item in todos],
    }


def create_milestone(
    session: Session, project_id: str, payload: MilestoneCreate
) -> Milestone:
    get_project(session, project_id)
    milestone = Milestone(
        project_id=project_id,
        title=payload.title,
        due_at=payload.due_at,
        status="open",
    )
    session.add(milestone)
    session.flush()
    return milestone


def get_milestone(session: Session, milestone_id: str) -> Milestone:
    milestone = session.get(Milestone, milestone_id)
    if milestone is None:
        raise AppError("NOT_FOUND", "里程碑不存在", 404, {"milestone_id": milestone_id})
    return milestone


def update_milestone(
    session: Session, milestone: Milestone, payload: MilestoneUpdate
) -> Milestone:
    data = payload.model_dump(exclude_unset=True)
    if "title" in data and not (data["title"] or "").strip():
        raise AppError("VALIDATION_ERROR", "里程碑标题不能为空", 422, {"field": "title"})
    for field in ("title", "due_at"):
        if field in data:
            setattr(milestone, field, data[field])
    if "status" in data and data["status"] != milestone.status:
        milestone.status = data["status"]
        if data["status"] == "done":
            milestone.completed_at = utcnow()
        else:
            milestone.completed_at = None
    session.flush()
    return milestone


def record_snapshot(
    session: Session,
    project: Project,
    snapshot: dict,
    error: str | None = None,
    github: dict | None = None,
    github_error: str | None = None,
) -> RepoSnapshot:
    row = RepoSnapshot(
        project_id=project.id,
        state="error" if error else snapshot.get("state", "ok"),
        error=error,
        branch=snapshot.get("branch"),
        upstream=snapshot.get("upstream"),
        ahead=snapshot.get("ahead"),
        behind=snapshot.get("behind"),
        dirty_files=snapshot.get("dirty_files"),
        staged_files=snapshot.get("staged_files"),
        untracked_files=snapshot.get("untracked_files"),
        last_commit_at=ensure_utc(snapshot.get("last_commit_at")),
        last_commit_subject=snapshot.get("last_commit_subject"),
        github_json=json.dumps(github, ensure_ascii=False) if github else None,
        github_error=github_error,
        scanned_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def scan_project(session: Session, project: Project) -> dict:
    import httpx

    from ..adapters.github_api import fetch_github_state, parse_github_remote
    from . import credentials
    from .settings import current_tz

    if not project.repo_path:
        raise AppError(
            "REPO_PATH_INVALID", "项目未关联仓库路径", 422, {"project_id": project.id}
        )
    from .repo_scanner import (
        ScanError,
        ensure_scan_path,
        is_git_repo,
        remote_url,
        scan_repo,
    )

    path = ensure_scan_path(project.repo_path)
    tz = current_tz(session)
    if not is_git_repo(path):
        snapshot = {
            "state": "no_git",
            "error": None,
            "branch": None,
            "upstream": None,
            "ahead": None,
            "behind": None,
            "dirty_files": None,
            "staged_files": None,
            "untracked_files": None,
            "last_commit_at": None,
            "last_commit_subject": None,
        }
        row = record_snapshot(session, project, snapshot)
        return {
            "snapshot": snapshot_out(row, tz),
            "health": project_health(session, project, tz),
        }

    try:
        snapshot = scan_repo(path)
    except ScanError as exc:
        snapshot = {
            "state": "error",
            "error": None,
            "branch": None,
            "upstream": None,
            "ahead": None,
            "behind": None,
            "dirty_files": None,
            "staged_files": None,
            "untracked_files": None,
            "last_commit_at": None,
            "last_commit_subject": None,
        }
        row = record_snapshot(session, project, snapshot, error=str(exc))
    else:
        github = None
        github_error = None
        parsed = parse_github_remote(remote_url(path))
        if parsed is not None:
            token = credentials.load_github_token()
            try:
                github = fetch_github_state(parsed[0], parsed[1], token)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 401:
                    github_error = "GitHub 令牌无效或已过期"
                elif status == 403:
                    github_error = "GitHub 拒绝访问：令牌权限不足或触发速率限制"
                elif status == 404:
                    github_error = "仓库不存在，或令牌无权访问该私有仓库"
                else:
                    github_error = f"GitHub 请求失败（HTTP {status}）"
            except Exception as exc:  # noqa: BLE001 - remote failure is partial
                github_error = f"GitHub 请求失败：{exc}"
        row = record_snapshot(
            session, project, snapshot, github=github, github_error=github_error
        )
    return {
        "snapshot": snapshot_out(row, tz),
        "health": project_health(session, project, tz),
    }
