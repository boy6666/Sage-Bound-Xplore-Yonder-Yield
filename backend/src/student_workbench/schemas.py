from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

WorkItemStatus = Literal["inbox", "planned", "in_progress", "done", "dismissed"]
Priority = Literal["low", "normal", "high", "urgent"]
ItemType = Literal["task", "assignment", "exam", "milestone"]
WorkItemSourceType = Literal["manual", "learning", "academic", "github", "project"]
ProjectStatus = Literal[
    "idea",
    "planning",
    "in_progress",
    "blocked",
    "waiting",
    "on_hold",
    "completed",
    "cancelled",
    "archived",
]
MilestoneStatus = Literal["open", "done"]
ConnectionKind = Literal["academic", "learning"]
Provider = Literal[
    "academic_fake", "learning_fake", "academic_portal_v1", "chaoxing_v1"
]


class WorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    item_type: ItemType = "task"
    priority: Priority = "normal"
    status: WorkItemStatus = "inbox"
    due_at: datetime | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    estimate_minutes: int | None = Field(default=None, ge=0)
    blocked_reason: str | None = None
    course_id: str | None = None
    project_id: str | None = None


class WorkItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    notes: str | None = None
    item_type: ItemType | None = None
    priority: Priority | None = None
    status: WorkItemStatus | None = None
    due_at: datetime | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    estimate_minutes: int | None = Field(default=None, ge=0)
    blocked_reason: str | None = None
    course_id: str | None = None
    project_id: str | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    status: ProjectStatus = "planning"
    repo_path: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: ProjectStatus | None = None
    status_reason: str | None = None
    resume_at: datetime | None = None
    next_action: str | None = None
    repo_path: str | None = None


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    due_at: date | None = None


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    due_at: date | None = None
    status: MilestoneStatus | None = None


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    code: str | None = None
    term: str | None = None
    teacher: str | None = None


class IdentityLink(BaseModel):
    course_id: str


class CreateCourseFromIdentity(BaseModel):
    name: str = Field(min_length=1, max_length=300)


class ConnectionCreate(BaseModel):
    kind: ConnectionKind
    provider: Provider
    display_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=500)
    save_password: bool = False


class ChallengeRequest(BaseModel):
    challenge_id: str
    code: str


class BootstrapComplete(BaseModel):
    timezone: str
    term_start_date: date | None = None


class SettingsPatch(BaseModel):
    timezone: str | None = None
    upcoming_days: int | None = Field(default=None, ge=0, le=365)
    stale_snapshot_hours: int | None = Field(default=None, ge=1, le=8760)
    inactive_days: int | None = Field(default=None, ge=0, le=365)
    save_platform_password: bool | None = None
    term_start_date: date | None = None


class HealthReasonOut(BaseModel):
    code: str
    label: str
    detail: str | None = None
    action: str | None = None


class HealthOut(BaseModel):
    level: str
    reasons: list[HealthReasonOut]


class WorkItemOut(BaseModel):
    id: str
    title: str
    notes: str | None
    item_type: str
    source_type: str
    status: str
    priority: str
    due_at: str | None
    planned_start_at: str | None
    planned_end_at: str | None
    estimate_minutes: int | None
    blocked_reason: str | None
    course_id: str | None
    course_name: str | None
    project_id: str | None
    project_name: str | None
    source_url: str | None
    external_id: str | None
    external_status: str | None
    needs_review: bool
    created_at: str | None
    updated_at: str | None


class WorkItemListOut(BaseModel):
    items: list[WorkItemOut]


class MilestoneOut(BaseModel):
    id: str
    title: str
    due_at: str | None
    status: str
    completed_at: str | None


class StatusHistoryOut(BaseModel):
    id: str
    from_status: str | None
    to_status: str
    reason: str | None
    changed_at: str | None


class RepoSnapshotOut(BaseModel):
    branch: str | None
    upstream: str | None
    ahead: int | None
    behind: int | None
    dirty_files: int | None
    staged_files: int | None
    untracked_files: int | None
    last_commit_at: str | None
    last_commit_subject: str | None
    scanned_at: str | None
    state: str
    error: str | None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    status_reason: str | None
    status_changed_at: str | None
    resume_at: str | None
    next_action: str | None
    next_action_updated_at: str | None
    repo_path: str | None
    open_todos: int
    milestones_total: int
    milestones_done: int
    health: HealthOut
    created_at: str | None
    updated_at: str | None


class ProjectListOut(BaseModel):
    items: list[ProjectOut]


class ProjectDetailOut(BaseModel):
    project: ProjectOut
    milestones: list[MilestoneOut]
    status_history: list[StatusHistoryOut]
    repo_snapshot: RepoSnapshotOut | None
    todos: list[WorkItemOut]


class ScanOut(BaseModel):
    snapshot: RepoSnapshotOut | None
    health: HealthOut


class CourseIdentityOut(BaseModel):
    id: str
    connection_id: str
    platform: str
    provider: str
    external_id: str
    external_name: str
    teacher: str | None
    match_status: str
    course_id: str | None


class NextClassOut(BaseModel):
    weekday: int
    start_time: str
    end_time: str
    location: str | None


class CourseOut(BaseModel):
    id: str
    name: str
    code: str | None
    term: str | None
    teacher: str | None
    identities: list[CourseIdentityOut]
    open_todos: int
    next_class: NextClassOut | None


class ScheduleEntryOut(BaseModel):
    id: str
    course_id: str
    course_name: str
    weekday: int
    start_time: str
    end_time: str
    location: str | None
    weeks: list[int]
    weeks_label: str


class CourseDetailOut(BaseModel):
    course: CourseOut
    schedule: list[ScheduleEntryOut]
    todos: list[WorkItemOut]


class CourseListOut(BaseModel):
    items: list[CourseOut]


class ScheduleItemOut(BaseModel):
    id: str
    title: str
    weekday: int
    kind: Literal["planned", "due"]
    time_label: str
    item_type: ItemType
    priority: Priority
    status: WorkItemStatus
    course_id: str | None
    course_name: str | None
    due_at: str | None
    planned_start_at: str | None


class ScheduleOut(BaseModel):
    term_start_date: str | None
    current_week: int | None
    week_start: str | None
    week_source: Literal["portal", "cached", "fallback", "computed"] | None
    entries: list[ScheduleEntryOut]
    items: list[ScheduleItemOut]
    missing_term_start: bool


class SuggestedCourseOut(BaseModel):
    course_id: str
    name: str
    reason: str


class UnmatchedIdentityOut(BaseModel):
    identity: CourseIdentityOut
    provider: str
    suggested: list[SuggestedCourseOut]


class UnmatchedListOut(BaseModel):
    items: list[UnmatchedIdentityOut]


class ConnectionOut(BaseModel):
    id: str
    kind: str
    provider: str
    display_name: str
    status: str
    account_label: str | None
    last_sync_at: str | None
    last_error: str | None
    credential_saved: bool


class SyncRunOut(BaseModel):
    id: str
    connection_id: str
    connection_name: str
    kind: str
    status: str
    started_at: str | None
    finished_at: str | None
    counts: dict[str, int]
    error_code: str | None
    error_message: str | None


class ConnectionListOut(BaseModel):
    items: list[ConnectionOut]


class SyncRunListOut(BaseModel):
    items: list[SyncRunOut]


class LoginResult(BaseModel):
    status: str
    challenge: dict[str, str] | None = None


class SyncStartOut(BaseModel):
    sync_run_id: str


class SettingsOut(BaseModel):
    setup_completed: bool
    timezone: str
    upcoming_days: int
    stale_snapshot_hours: int
    inactive_days: int
    save_platform_password: bool
    term_start_date: str | None


class BootstrapOut(BaseModel):
    setup_completed: bool
    timezone: str
    today: str
    counts: dict[str, int]


class TodayClassOut(BaseModel):
    course_id: str
    course_name: str
    start_time: str
    end_time: str
    location: str | None
    open_todos: int
    status: str = "normal"
    adjustment_note: str | None = None


class ProjectRiskOut(BaseModel):
    project_id: str
    name: str
    level: str
    reason: str


class TodayOut(BaseModel):
    date: str
    timezone: str
    classes_today: list[TodayClassOut]
    overdue: list[WorkItemOut]
    today_planned: list[WorkItemOut]
    upcoming_unplanned: list[WorkItemOut]
    blocked: list[WorkItemOut]
    project_risks: list[ProjectRiskOut]
    data_warnings: list[str]
