# 前端 / 后端共享契约（P0 切片 v0.1）

本文件是前后端并行开发的唯一接口契约。实现以本文件为准；`BACKEND_STRUCTURE.md` 提供设计背景，
若两者冲突，以本文件为准（本文件是已裁剪的可实施子集）。

- Base URL：`/api/v1`（开发时 Vite 将 `/api` 代理到 `http://127.0.0.1:8765`）
- 内容类型：`application/json; charset=utf-8`
- 所有写请求（POST/PATCH/PUT/DELETE）必须携带：
  - `Origin: http://127.0.0.1:{port}` 或 `http://localhost:{port}`（同源）
  - `X-Student-Workbench-Client: web`
  - `Content-Type: application/json`
- 时间：ISO 8601 带时区偏移，如 `2026-11-24T23:59:00+08:00`；纯日期 `2026-11-24`
- ID：UUID4 字符串
- 错误体：

```json
{"error": {"code": "PROJECT_STATUS_REASON_REQUIRED", "message": "受阻状态必须填写原因", "details": {}}}
```

## 1. 枚举

| 枚举 | 取值 |
|---|---|
| `WorkItemStatus` | `inbox` `planned` `in_progress` `done` `dismissed` |
| `Priority` | `low` `normal` `high` `urgent` |
| `ItemType` | `task` `assignment` `exam` `milestone` |
| `SourceType` | `manual` `learning` `academic` `github` `project` |
| `ProjectStatus` | `idea` `planning` `in_progress` `blocked` `waiting` `on_hold` `completed` `cancelled` `archived` |
| `HealthLevel` | `green` `yellow` `red` `unknown` `inactive` |
| `ConnectionKind` | `academic` `learning` |
| `ConnectionStatus` | `unconfigured` `needs_auth` `ready` `syncing` `error` |
| `SyncStatus` | `running` `succeeded` `partial` `failed` `needs_auth` `interrupted` |
| `MilestoneStatus` | `open` `done` |

## 2. 对象

### WorkItem

```json
{
  "id": "uuid",
  "title": "操作系统实验二",
  "notes": "先补全页表部分",
  "item_type": "assignment",
  "source_type": "learning",
  "status": "inbox",
  "priority": "high",
  "due_at": "2026-11-27T23:59:00+08:00",
  "planned_start_at": null,
  "planned_end_at": null,
  "estimate_minutes": 90,
  "blocked_reason": null,
  "course_id": "uuid|null",
  "course_name": "操作系统|null",
  "project_id": "uuid|null",
  "project_name": "个人工作台|null",
  "source_url": "https://...|null",
  "external_id": "hw-1001|null",
  "external_status": "未提交|null",
  "needs_review": false,
  "created_at": "...",
  "updated_at": "..."
}
```

### Project

```json
{
  "id": "uuid",
  "name": "个人工作台",
  "description": "本地优先的学生执行系统",
  "status": "in_progress",
  "status_reason": null,
  "status_changed_at": "...",
  "resume_at": null,
  "next_action": "完成今日页聚合",
  "next_action_updated_at": "...",
  "repo_path": "E:\\code\\workbench",
  "open_todos": 3,
  "milestones_total": 2,
  "milestones_done": 1,
  "health": {"level": "yellow", "reasons": [{"code": "REPO_DIRTY", "label": "工作区有未提交修改", "detail": "2 个文件", "action": "repo"}]},
  "created_at": "...",
  "updated_at": "..."
}
```

`health.reasons[].action` ∈ `repo` `milestone` `next_action` `sync` `status` `null`。

### ProjectDetail（GET /projects/{id}）

```json
{
  "project": { "...Project": true },
  "milestones": [{"id": "uuid", "title": "M1", "due_at": "2026-12-01", "status": "open", "completed_at": null}],
  "status_history": [{"id": "uuid", "from_status": "planning", "to_status": "in_progress", "reason": null, "changed_at": "..."}],
  "repo_snapshot": {
    "branch": "main", "upstream": "origin/main", "ahead": 2, "behind": 0,
    "dirty_files": 1, "staged_files": 0, "untracked_files": 1,
    "last_commit_at": "...", "last_commit_subject": "feat: today", "scanned_at": "...",
    "state": "ok", "error": null
  },
  "todos": [{"...WorkItem": true}]
}
```

`repo_snapshot` 为 `null` 表示还没扫描。`ahead/behind` 为 `null` 表示 unknown（无 upstream），不得当作 0。

### Course

```json
{
  "id": "uuid",
  "name": "操作系统",
  "code": "CS301",
  "term": "2026-2027-1",
  "teacher": "张老师",
  "identities": [
    {"id": "uuid", "connection_id": "uuid", "platform": "academic", "provider": "academic_fake", "external_id": "c-1", "external_name": "操作系统", "teacher": "张老师", "match_status": "auto_exact", "course_id": "uuid"}
  ],
  "open_todos": 2,
  "next_class": {"weekday": 1, "start_time": "08:00", "end_time": "09:40", "location": "教三-201"}
}
```

`match_status` ∈ `auto_exact` `manual` `unmatched` `ignored`。

### ScheduleEntry

```json
{"id": "uuid", "course_id": "uuid", "course_name": "操作系统", "weekday": 1, "start_time": "08:00", "end_time": "09:40", "location": "教三-201", "weeks": [1,2,3,4,5,6,7,8], "weeks_label": "1-8周"}
```

`weekday`：1=周一 … 7=周日。

### Health

```json
{"level": "red", "reasons": [{"code": "PROJECT_BLOCKED", "label": "项目受阻", "detail": "等助教回复环境问题", "action": "status"}]}
```

## 3. 接口

### 3.1 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` | `{"status":"ok","version":"0.1.0"}`（不带 /api/v1 前缀） |
| GET | `/api/v1/bootstrap` | `{"setup_completed":false,"timezone":"Asia/Shanghai","today":"2026-11-23","counts":{"inbox":0,"today":0,"projects":0,"courses":0}}` |
| POST | `/api/v1/bootstrap/complete` | body `{"timezone":"Asia/Shanghai","term_start_date":"2026-09-01"}` → bootstrap |
| GET | `/api/v1/settings` | Settings |
| PATCH | `/api/v1/settings` | 部分更新 → Settings |

Settings：

```json
{
  "setup_completed": true,
  "timezone": "Asia/Shanghai",
  "upcoming_days": 7,
  "stale_snapshot_hours": 72,
  "inactive_days": 14,
  "save_platform_password": false,
  "term_start_date": "2026-09-01"
}
```

### 3.2 事项

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/work-items` | 查询参数：`status` `source_type` `project_id` `course_id` `q` `limit`(默认 100) → `{"items":[WorkItem]}` |
| POST | `/api/v1/work-items` | body：`title`(必填) `notes` `item_type` `priority` `status` `due_at` `planned_start_at` `planned_end_at` `estimate_minutes` `blocked_reason` `course_id` `project_id` → 201 WorkItem |
| GET | `/api/v1/work-items/{id}` | WorkItem |
| PATCH | `/api/v1/work-items/{id}` | 同上字段部分更新；`status` 变更写 `completed_at`（done 时） |
| DELETE | `/api/v1/work-items/{id}` | 204 |

### 3.3 项目

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/projects` | `?status=` → `{"items":[Project]}` |
| POST | `/api/v1/projects` | `{"name","description","status","repo_path"}` → 201 Project |
| GET | `/api/v1/projects/{id}` | ProjectDetail |
| PATCH | `/api/v1/projects/{id}` | `name` `description` `status` `status_reason` `resume_at` `next_action` `repo_path` |
| DELETE | `/api/v1/projects/{id}` | 204（软删除到 archived 不做，直接删除并级联 todos 置空 project_id） |
| POST | `/api/v1/projects/{id}/milestones` | `{"title","due_at"}` → 201 Milestone |
| PATCH | `/api/v1/milestones/{id}` | `title` `due_at` `status` |
| POST | `/api/v1/projects/{id}/todos` | 同 POST /work-items，自动 `project_id`、`source_type=project`、`item_type=task` |
| POST | `/api/v1/projects/{id}/scan` | 扫描本地 Git → `{"snapshot": RepoSnapshot|null, "health": Health}` |

`PATCH /projects/{id}` 规则：

- `status` 变为 `blocked|waiting|on_hold|cancelled` 且 `status_reason` 为空/空白 → 422 `PROJECT_STATUS_REASON_REQUIRED`
- 每次 status 变化追加 `project_status_history`，`status_changed_at` 更新
- `next_action` 变化更新 `next_action_updated_at`

### 3.4 课程

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/courses` | `{"items":[Course]}` |
| POST | `/api/v1/courses` | `{"name","code","term","teacher"}` → 201 |
| GET | `/api/v1/courses/{id}` | `{"course":Course,"schedule":[ScheduleEntry],"todos":[WorkItem]}` |
| GET | `/api/v1/courses/schedule?week=` | `{"term_start_date":"2026-09-01","current_week":12,"entries":[ScheduleEntry],"missing_term_start":false}` |
| GET | `/api/v1/course-identities/unmatched` | `{"items":[{"identity":{...},"provider":"learning_fake","suggested":[{"course_id","name","reason"}]}]}` |
| POST | `/api/v1/course-identities/{id}/link` | `{"course_id"}` → 200 identity；同事务把该身份下课程表与 WorkItem 改绑 |
| POST | `/api/v1/course-identities/{id}/unlink` | → 200 identity（match_status=unmatched，不删除作业） |
| POST | `/api/v1/course-identities/{id}/create-course` | `{"name"}` → 201 Course 并关联 |

### 3.5 连接与同步

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/connections` | `{"items":[Connection]}` |
| POST | `/api/v1/connections` | `{"kind","provider","display_name"}`；provider ∈ `academic_fake` `learning_fake` `academic_portal_v1` `chaoxing_v1` |
| POST | `/api/v1/connections/{id}/login` | `{"username","password","save_password"}` → `{"status":"ready"}` 或 `{"status":"challenge","challenge":{"id","prompt"}}` |
| POST | `/api/v1/connections/{id}/login/challenge` | `{"challenge_id","code"}` → `{"status":"ready"}`；错误码 `PLATFORM_LOGIN_FAILED` |
| POST | `/api/v1/connections/{id}/sync` | 202 `{"sync_run_id":"uuid"}`；同连接已有活动运行时返回同一个 `sync_run_id` |
| GET | `/api/v1/sync-runs/{id}` | SyncRun |
| GET | `/api/v1/sync-runs?limit=20` | `{"items":[SyncRun]}` |
| DELETE | `/api/v1/connections/{id}` | 204 |

Connection：

```json
{"id":"uuid","kind":"learning","provider":"learning_fake","display_name":"学习通（示例）","status":"ready","account_label":"demo","last_sync_at":"...","last_error":null,"credential_saved":false}
```

SyncRun：

```json
{"id":"uuid","connection_id":"uuid","connection_name":"学习通（示例）","kind":"learning","status":"succeeded","started_at":"...","finished_at":"...","counts":{"courses":3,"items":8,"schedule":0},"error_code":null,"error_message":null}
```

### 3.6 今日

`GET /api/v1/dashboard/today?date=2026-11-23`

```json
{
  "date": "2026-11-23",
  "timezone": "Asia/Shanghai",
  "classes_today": [{"course_id":"uuid","course_name":"操作系统","start_time":"08:00","end_time":"09:40","location":"教三-201","open_todos":2}],
  "overdue": [WorkItem],
  "today_planned": [WorkItem],
  "upcoming_unplanned": [WorkItem],
  "blocked": [WorkItem],
  "project_risks": [{"project_id":"uuid","name":"个人工作台","level":"red","reason":"项目受阻：等助教回复"}],
  "data_warnings": ["学习通（示例）最近一次同步失败"]
}
```

分组规则：

- 只考虑 `status` ∈ `inbox|planned|in_progress`
- `overdue`：`due_at` 的本地日期 < today
- `today_planned`：`planned_start_at` 的本地日期 == today（含逾期但今天计划）
- `upcoming_unplanned`：`due_at` 本地日期在 `[today, today+upcoming_days]` 且无 `planned_start_at`，且不属于 `today_planned`
- `blocked`：`blocked_reason` 非空
- `project_risks`：只含 health 为 `red` 的项目；`reason` 取第一条 red 原因
- `classes_today`：按 `term_start_date` 计算教学周与单双周；不生成 WorkItem
- 同一事项只出现在一个分组，优先级：overdue > today_planned > upcoming_unplanned > blocked

## 4. 错误码

| code | HTTP | 场景 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 请求体校验失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `PROJECT_STATUS_REASON_REQUIRED` | 422 | 受阻/等待/暂停/取消未填原因 |
| `WORK_ITEM_INVALID_TRANSITION` | 409 | 非法状态流转（done → in_progress 允许，dismissed 不可再激活） |
| `PLATFORM_NOT_CONFIGURED` | 409 | 真实适配器未实现/未配置 |
| `PLATFORM_AUTH_REQUIRED` | 409 | 会话失效，需要重新登录 |
| `PLATFORM_STRUCTURE_CHANGED` | 502 | 页面结构变化，解析失败 |
| `SYNC_ALREADY_RUNNING` | 202 | 同连接已有运行，返回同一个 sync_run_id |
| `REPO_PATH_INVALID` | 422 | 仓库路径不存在或不是 Git 仓库 |
| `FORBIDDEN_ORIGIN` | 403 | 写请求来源不合法 |

## 5. P0 明确不做

- 真实 `academic_portal_v1` / `chaoxing_v1` 解析（本轮返回 `PLATFORM_NOT_CONFIGURED`，不伪造接入成功）
- GitHub 远端同步（健康规则预留 `remote`，本轮只用本地 Git）
- 自动同步、通知、周报、AI、导出
- 用户登录系统（仅本机 127.0.0.1 + Origin/自定义头校验）
