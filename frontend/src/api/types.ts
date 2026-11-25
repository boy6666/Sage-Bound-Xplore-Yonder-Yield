export type WorkItemStatus = 'inbox' | 'planned' | 'in_progress' | 'done' | 'dismissed'
export type Priority = 'low' | 'normal' | 'high' | 'urgent'
export type ItemType = 'task' | 'assignment' | 'exam' | 'milestone'
export type SourceType = 'manual' | 'learning' | 'academic' | 'github' | 'project'
export type ProjectStatus =
  | 'idea'
  | 'planning'
  | 'in_progress'
  | 'blocked'
  | 'waiting'
  | 'on_hold'
  | 'completed'
  | 'cancelled'
  | 'archived'
export type HealthLevel = 'green' | 'yellow' | 'red' | 'unknown' | 'inactive'
export type HealthAction = 'repo' | 'milestone' | 'next_action' | 'sync' | 'status' | null
export type ConnectionKind = 'academic' | 'learning'
export type ConnectionStatus = 'unconfigured' | 'needs_auth' | 'ready' | 'syncing' | 'error'
export type SyncStatus = 'running' | 'succeeded' | 'partial' | 'failed' | 'needs_auth' | 'interrupted'
export type MilestoneStatus = 'open' | 'done'
export type MatchStatus = 'auto_exact' | 'manual' | 'unmatched' | 'ignored'
export type Provider =
  | 'academic_fake'
  | 'learning_fake'
  | 'academic_portal_v1'
  | 'chaoxing_v1'

export interface HealthReason {
  code: string
  label: string
  detail: string | null
  action: HealthAction
}

export interface Health {
  level: HealthLevel
  reasons: HealthReason[]
}

export interface WorkItem {
  id: string
  title: string
  notes: string | null
  item_type: ItemType
  source_type: SourceType
  status: WorkItemStatus
  priority: Priority
  due_at: string | null
  planned_start_at: string | null
  planned_end_at: string | null
  estimate_minutes: number | null
  blocked_reason: string | null
  course_id: string | null
  course_name: string | null
  project_id: string | null
  project_name: string | null
  source_url: string | null
  external_id: string | null
  external_status: string | null
  needs_review: boolean
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  name: string
  description: string | null
  status: ProjectStatus
  status_reason: string | null
  status_changed_at: string | null
  resume_at: string | null
  next_action: string | null
  next_action_updated_at: string | null
  repo_path: string | null
  open_todos: number
  milestones_total: number
  milestones_done: number
  health: Health
  created_at: string
  updated_at: string
}

export interface Milestone {
  id: string
  title: string
  due_at: string | null
  status: MilestoneStatus
  completed_at: string | null
}

export interface StatusHistoryEntry {
  id: string
  from_status: ProjectStatus | null
  to_status: ProjectStatus
  reason: string | null
  changed_at: string
}

export interface GithubState {
  state: 'ok' | 'error' | string
  error: string | null
  owner?: string
  repo?: string
  private?: boolean
  default_branch?: string | null
  open_issues?: number
  open_pulls?: number
  oldest_pull_days?: number | null
  ci_status?: 'success' | 'failure' | 'pending' | 'none' | string
  ci_name?: string | null
  pushed_at?: string | null
  fetched_at?: string | null
}

export interface RepoSnapshot {
  branch: string | null
  upstream: string | null
  ahead: number | null
  behind: number | null
  dirty_files: number | null
  staged_files: number | null
  untracked_files: number | null
  last_commit_at: string | null
  last_commit_subject: string | null
  scanned_at: string | null
  state: 'ok' | 'error' | string
  error: string | null
  github: GithubState | null
  github_error: string | null
}

export interface ProjectDetail {
  project: Project
  milestones: Milestone[]
  status_history: StatusHistoryEntry[]
  repo_snapshot: RepoSnapshot | null
  todos: WorkItem[]
}

export interface CourseIdentity {
  id: string
  connection_id: string
  platform: string
  provider: string
  external_id: string
  external_name: string
  teacher: string | null
  match_status: MatchStatus
  course_id: string | null
}

export interface NextClass {
  weekday: number
  start_time: string
  end_time: string
  location: string | null
}

export interface Course {
  id: string
  name: string
  code: string | null
  term: string | null
  teacher: string | null
  identities: CourseIdentity[]
  open_todos: number
  next_class: NextClass | null
}

export interface ScheduleEntry {
  id: string
  course_id: string
  course_name: string
  weekday: number
  start_time: string
  end_time: string
  location: string | null
  weeks: number[]
  weeks_label: string
}

export interface CourseDetailResponse {
  course: Course
  schedule: ScheduleEntry[]
  todos: WorkItem[]
}

export interface ScheduleItem {
  id: string
  title: string
  weekday: number
  kind: 'planned' | 'due'
  time_label: string
  item_type: WorkItem['item_type']
  priority: WorkItem['priority']
  status: WorkItem['status']
  course_id: string | null
  course_name: string | null
  due_at: string | null
  planned_start_at: string | null
}

export interface ScheduleResponse {
  term_start_date: string | null
  current_week: number
  week_start: string | null
  week_source: 'portal' | 'cached' | 'fallback' | 'computed' | null
  entries: ScheduleEntry[]
  items: ScheduleItem[]
  missing_term_start: boolean
}

export interface UnmatchedIdentity {
  identity: CourseIdentity
  provider: string
  suggested: { course_id: string; name: string; reason: string }[]
}

export interface Connection {
  id: string
  kind: ConnectionKind
  provider: string
  display_name: string
  status: ConnectionStatus
  account_label: string | null
  last_sync_at: string | null
  last_error: string | null
  credential_saved: boolean
}

export interface SyncRunCounts {
  courses: number
  items: number
  schedule: number
  adjustments?: number
}

export interface SyncRun {
  id: string
  connection_id: string
  connection_name: string
  kind: ConnectionKind
  status: SyncStatus
  started_at: string
  finished_at: string | null
  counts: SyncRunCounts
  error_code: string | null
  error_message: string | null
}

export interface Bootstrap {
  setup_completed: boolean
  timezone: string
  today: string
  counts: {
    inbox: number
    today: number
    projects: number
    courses: number
  }
}

export interface Settings {
  setup_completed: boolean
  timezone: string
  upcoming_days: number
  stale_snapshot_hours: number
  inactive_days: number
  save_platform_password: boolean
  term_start_date: string | null
  github_token_saved: boolean
}

export interface TodayClass {
  course_id: string
  course_name: string
  start_time: string
  end_time: string
  location: string | null
  open_todos: number
  status?: 'normal' | 'cancelled' | 'moved' | 'makeup'
  adjustment_note?: string | null
}

export interface ProjectRisk {
  project_id: string
  name: string
  level: HealthLevel
  reason: string
}

export interface TodayDashboard {
  date: string
  timezone: string
  classes_today: TodayClass[]
  overdue: WorkItem[]
  today_planned: WorkItem[]
  upcoming_unplanned: WorkItem[]
  blocked: WorkItem[]
  project_risks: ProjectRisk[]
  data_warnings: string[]
}

export interface WorkItemFilters {
  status?: WorkItemStatus | ''
  source_type?: SourceType | ''
  project_id?: string
  course_id?: string
  q?: string
  limit?: number
}

export interface WorkItemInput {
  title: string
  notes?: string | null
  item_type?: ItemType
  priority?: Priority
  status?: WorkItemStatus
  due_at?: string | null
  planned_start_at?: string | null
  planned_end_at?: string | null
  estimate_minutes?: number | null
  blocked_reason?: string | null
  course_id?: string | null
  project_id?: string | null
}

export type WorkItemPatch = Partial<WorkItemInput>

export interface ProjectInput {
  name: string
  description?: string | null
  status?: ProjectStatus
  repo_path?: string | null
}

export interface ProjectPatch {
  name?: string
  description?: string | null
  status?: ProjectStatus
  status_reason?: string | null
  resume_at?: string | null
  next_action?: string | null
  repo_path?: string | null
}

export interface LoginChallenge {
  id: string
  prompt: string
}

export interface LoginResponse {
  status: 'ready' | 'challenge'
  challenge?: LoginChallenge
}

export interface ApiErrorPayload {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
    request_id?: string
  }
}
