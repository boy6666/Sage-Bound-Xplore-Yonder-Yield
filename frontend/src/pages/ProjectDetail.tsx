import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { Milestone, ProjectStatus, WorkItem } from '../api/types'
import {
  useAddMilestone,
  useAddProjectTodo,
  useProject,
  useScanProject,
  useUpdateMilestone,
  useUpdateProject,
  useUpdateWorkItem,
} from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { Field } from '../components/Field'
import { HealthBadge } from '../components/HealthBadge'
import { StatusBadge } from '../components/StatusBadge'
import { WorkItemRow } from '../components/WorkItemRow'
import { formatDate, formatDateTime, isoWithOffset, localInputToISO, planTodayISO } from '../lib/date'
import {
  HEALTH_DESCRIPTIONS,
  PROJECT_STATUS_LABELS,
  PROJECT_STATUS_OPTIONS,
  errorMessage,
  requiresStatusReason,
} from '../lib/format'

function unknownNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '未知' : String(value)
}

function MilestoneRow({
  milestone,
  busy,
  onToggle,
}: {
  milestone: Milestone
  busy: boolean
  onToggle: (milestone: Milestone) => void
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-edge bg-surface-2/40 px-3 py-2">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-sm text-ink">
          <span
            aria-hidden="true"
            className={milestone.status === 'done' ? 'text-emerald-300' : 'text-muted'}
          >
            {milestone.status === 'done' ? '✓' : '○'}
          </span>
          <span className={milestone.status === 'done' ? 'line-through text-muted' : ''}>
            {milestone.title}
          </span>
        </p>
        <p className="text-xs text-muted">
          截止：{milestone.due_at ? formatDate(milestone.due_at) : '未设置'}
          {milestone.completed_at
            ? ` · 完成于 ${formatDateTime(milestone.completed_at)}`
            : ''}
        </p>
      </div>
      <button
        type="button"
        className="btn btn-sm"
        disabled={busy}
        aria-label={`${milestone.status === 'done' ? '恢复' : '完成'}里程碑「${milestone.title}」`}
        onClick={() => onToggle(milestone)}
      >
        {milestone.status === 'done' ? '恢复未完成' : '标记完成'}
      </button>
    </li>
  )
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const projectQuery = useProject(id)
  const updateProject = useUpdateProject()
  const addMilestone = useAddMilestone()
  const updateMilestone = useUpdateMilestone()
  const addTodo = useAddProjectTodo()
  const updateTodo = useUpdateWorkItem()
  const scan = useScanProject()

  const project = projectQuery.data?.project

  const [status, setStatus] = useState<ProjectStatus>('planning')
  const [reason, setReason] = useState('')
  const [resumeAt, setResumeAt] = useState('')
  const [statusError, setStatusError] = useState<string | null>(null)
  const [statusSuccess, setStatusSuccess] = useState<string | null>(null)

  const [nextAction, setNextAction] = useState('')
  const [nextActionSaved, setNextActionSaved] = useState(false)

  const [milestoneTitle, setMilestoneTitle] = useState('')
  const [milestoneDue, setMilestoneDue] = useState('')
  const [milestoneError, setMilestoneError] = useState<string | null>(null)

  const [todoTitle, setTodoTitle] = useState('')
  const [todoDue, setTodoDue] = useState('')
  const [todoPlanned, setTodoPlanned] = useState('')
  const [todoError, setTodoError] = useState<string | null>(null)
  const [planDates, setPlanDates] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!project) return
    setStatus(project.status)
    setReason(project.status_reason ?? '')
    setResumeAt(project.resume_at ? project.resume_at.slice(0, 10) : '')
    setNextAction(project.next_action ?? '')
  }, [
    project?.id,
    project?.status,
    project?.status_reason,
    project?.resume_at,
    project?.next_action,
  ])

  if (!id) {
    return <ErrorState error={new Error('缺少项目 ID')} title="无法打开项目" />
  }

  if (projectQuery.isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        <div className="h-8 w-48 animate-pulse rounded bg-surface-2" />
        <div className="h-40 animate-pulse rounded-card bg-surface" />
        <p className="text-xs text-muted">正在加载项目详情…</p>
      </div>
    )
  }

  if (projectQuery.isError) {
    return (
      <div className="space-y-3">
        <ErrorState
          error={projectQuery.error}
          title="项目详情加载失败"
          onRetry={() => void projectQuery.refetch()}
        />
        <Link className="btn btn-sm" to="/projects">
          返回项目列表
        </Link>
      </div>
    )
  }

  const data = projectQuery.data
  const current = data.project
  const snapshot = data.repo_snapshot

  const handleStatusSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    setStatusSuccess(null)
    if (requiresStatusReason(status) && reason.trim() === '') {
      setStatusError('受阻、等待、暂停或取消状态必须填写具体原因，本次未提交。')
      return
    }
    setStatusError(null)
    updateProject.mutate(
      {
        id: current.id,
        patch: {
          status,
          status_reason: reason.trim() === '' ? null : reason.trim(),
          resume_at: resumeAt === '' ? null : resumeAt,
        },
      },
      {
        onSuccess: () => {
          setStatusSuccess('项目状态已更新，状态历史已追加。')
        },
      },
    )
  }

  const handleNextActionSave = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    setNextActionSaved(false)
    updateProject.mutate(
      { id: current.id, patch: { next_action: nextAction.trim() === '' ? null : nextAction.trim() } },
      { onSuccess: () => setNextActionSaved(true) },
    )
  }

  const handleMilestoneSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!milestoneTitle.trim()) {
      setMilestoneError('里程碑标题不能为空。')
      return
    }
    setMilestoneError(null)
    addMilestone.mutate(
      {
        projectId: current.id,
        title: milestoneTitle.trim(),
        due_at: milestoneDue === '' ? null : milestoneDue,
      },
      {
        onSuccess: () => {
          setMilestoneTitle('')
          setMilestoneDue('')
        },
      },
    )
  }

  const handleTodoSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!todoTitle.trim()) {
      setTodoError('待办标题不能为空。')
      return
    }
    setTodoError(null)
    addTodo.mutate(
      {
        projectId: current.id,
        input: {
          title: todoTitle.trim(),
          due_at: localInputToISO(todoDue),
          planned_start_at: localInputToISO(todoPlanned),
          status: todoPlanned ? 'planned' : 'inbox',
        },
      },
      {
        onSuccess: () => {
          setTodoTitle('')
          setTodoDue('')
          setTodoPlanned('')
        },
      },
    )
  }

  const handlePlanDate = (item: WorkItem): void => {
    const value = planDates[item.id]
    if (!value) return
    updateTodo.mutate({
      id: item.id,
      patch: {
        status: 'planned',
        planned_start_at: isoWithOffset(new Date(`${value}T09:00:00`)),
      },
    })
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <Link className="text-xs text-muted hover:text-accent" to="/projects">
            ← 返回项目列表
          </Link>
          <h1 className="break-words text-xl font-semibold text-ink">{current.name}</h1>
          {current.description ? (
            <p className="max-w-3xl text-sm text-muted">{current.description}</p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <HealthBadge level={current.health.level} />
            <StatusBadge kind="project" status={current.status} reason={current.status_reason} />
            {current.resume_at ? (
              <span className="text-xs text-muted">恢复日期：{formatDate(current.resume_at)}</span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-col items-start gap-1 text-right">
          <p className="text-xs text-muted">未完成项目待办</p>
          <p className="text-2xl font-semibold text-ink">{current.open_todos}</p>
        </div>
      </div>

      {statusSuccess ? (
        <p role="status" className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          {statusSuccess}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card card-pad space-y-3">
          <h2 className="text-sm font-semibold text-ink">生命周期状态</h2>
          <form className="space-y-3" onSubmit={handleStatusSubmit}>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="项目状态" htmlFor="project-status-select">
                <select
                  id="project-status-select"
                  className="input"
                  value={status}
                  onChange={(event) => {
                    setStatus(event.target.value as ProjectStatus)
                    setStatusError(null)
                    setStatusSuccess(null)
                  }}
                >
                  {PROJECT_STATUS_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {PROJECT_STATUS_LABELS[value]}
                    </option>
                  ))}
                </select>
              </Field>
              <Field
                label="恢复日期"
                htmlFor="project-resume-date"
                hint="等待或暂停状态可填写恢复日期。"
              >
                <input
                  id="project-resume-date"
                  className="input"
                  type="date"
                  value={resumeAt}
                  onChange={(event) => setResumeAt(event.target.value)}
                />
              </Field>
            </div>

            <Field
              label="状态原因"
              htmlFor="project-status-reason"
              required={requiresStatusReason(status)}
              hint={
                requiresStatusReason(status)
                  ? '当前状态必须说明具体原因，例如等待谁、什么事件或阻塞问题。'
                  : '可选，用于记录本次状态变更的背景。'
              }
            >
              <textarea
                id="project-status-reason"
                className="input min-h-20"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder={
                  requiresStatusReason(status)
                    ? '请填写具体原因（必填）'
                    : '可补充说明'
                }
              />
            </Field>

            {statusError ? (
              <p role="alert" className="text-sm font-medium text-rose-300">
                {statusError}
              </p>
            ) : null}
            {updateProject.isError ? (
              <p role="alert" className="text-sm text-rose-300">
                {errorMessage(updateProject.error)}
              </p>
            ) : null}

            <button type="submit" className="btn btn-primary" disabled={updateProject.isPending}>
              {updateProject.isPending ? '正在保存…' : '保存状态'}
            </button>
          </form>
        </section>

        <section className="card card-pad space-y-3">
          <h2 className="text-sm font-semibold text-ink">下一步行动</h2>
          <form className="space-y-3" onSubmit={handleNextActionSave}>
            <Field
              label="当前焦点"
              htmlFor="project-next-action"
              hint={
                current.next_action_updated_at
                  ? `上次更新：${formatDateTime(current.next_action_updated_at)}`
                  : '尚未设置下一步行动会触发黄色健康原因。'
              }
            >
              <input
                id="project-next-action"
                className="input"
                value={nextAction}
                onChange={(event) => {
                  setNextAction(event.target.value)
                  setNextActionSaved(false)
                }}
                placeholder="例如：完成今日页聚合"
              />
            </Field>
            {nextActionSaved ? (
              <p role="status" className="text-xs text-emerald-300">
                下一步行动已保存。
              </p>
            ) : null}
            <button type="submit" className="btn" disabled={updateProject.isPending}>
              保存下一步
            </button>
          </form>

          <div className="divider pt-3">
            <h3 className="pt-3 text-xs font-semibold uppercase tracking-wide text-muted">
              健康原因
            </h3>
            <p className="mt-1 text-xs text-muted">
              {HEALTH_DESCRIPTIONS[current.health.level]}
            </p>
            {current.health.reasons.length === 0 ? (
              <p className="mt-2 text-xs text-muted">
                当前未返回具体原因；这不等于项目一定健康。
              </p>
            ) : (
              <ul className="mt-2 space-y-1.5">
                {current.health.reasons.map((item) => (
                  <li key={`${item.code}-${item.label}`} className="text-xs">
                    <span className="font-medium text-ink">{item.label}</span>
                    {item.detail ? <span className="text-muted"> — {item.detail}</span> : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      <section className="card card-pad space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">里程碑</h2>
          <p className="text-xs text-muted">
            {current.milestones_done}/{current.milestones_total} 已完成
          </p>
        </div>
        {data.milestones.length === 0 ? (
          <p className="text-xs text-muted">还没有里程碑。</p>
        ) : (
          <ul className="space-y-2">
            {data.milestones.map((milestone) => (
              <MilestoneRow
                key={milestone.id}
                milestone={milestone}
                busy={updateMilestone.isPending}
                onToggle={(target) =>
                  updateMilestone.mutate({
                    id: target.id,
                    projectId: current.id,
                    patch: { status: target.status === 'done' ? 'open' : 'done' },
                  })
                }
              />
            ))}
          </ul>
        )}
        <form className="flex flex-wrap items-end gap-2 pt-2" onSubmit={handleMilestoneSubmit}>
          <Field label="新里程碑标题" htmlFor="milestone-title" className="min-w-48 flex-1 space-y-1">
            <input
              id="milestone-title"
              className="input"
              value={milestoneTitle}
              onChange={(event) => setMilestoneTitle(event.target.value)}
              placeholder="例如：M2 完成同步中心"
            />
          </Field>
          <Field label="截止日期" htmlFor="milestone-due" className="w-40 space-y-1">
            <input
              id="milestone-due"
              className="input"
              type="date"
              value={milestoneDue}
              onChange={(event) => setMilestoneDue(event.target.value)}
            />
          </Field>
          <button type="submit" className="btn" disabled={addMilestone.isPending}>
            添加里程碑
          </button>
        </form>
        {milestoneError ? (
          <p role="alert" className="text-sm text-rose-300">
            {milestoneError}
          </p>
        ) : null}
        {addMilestone.isError ? (
          <p role="alert" className="text-sm text-rose-300">
            {errorMessage(addMilestone.error)}
          </p>
        ) : null}
      </section>

      <section className="card card-pad space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">项目待办</h2>
          <p className="text-xs text-muted">{data.todos.length} 项</p>
        </div>
        <form className="space-y-3" onSubmit={handleTodoSubmit}>
          <div className="grid gap-3 md:grid-cols-3">
            <Field label="待办标题" htmlFor="todo-title" required>
              <input
                id="todo-title"
                className="input"
                value={todoTitle}
                onChange={(event) => setTodoTitle(event.target.value)}
                placeholder="例如：补全今日页空状态"
              />
            </Field>
            <Field label="截止时间" htmlFor="todo-due">
              <input
                id="todo-due"
                className="input"
                type="datetime-local"
                value={todoDue}
                onChange={(event) => setTodoDue(event.target.value)}
              />
            </Field>
            <Field label="计划开始" htmlFor="todo-planned">
              <input
                id="todo-planned"
                className="input"
                type="datetime-local"
                value={todoPlanned}
                onChange={(event) => setTodoPlanned(event.target.value)}
              />
            </Field>
          </div>
          {todoError ? (
            <p role="alert" className="text-sm text-rose-300">
              {todoError}
            </p>
          ) : null}
          {addTodo.isError ? (
            <p role="alert" className="text-sm text-rose-300">
              {errorMessage(addTodo.error)}
            </p>
          ) : null}
          <button type="submit" className="btn" disabled={addTodo.isPending}>
            新增项目待办
          </button>
        </form>

        {data.todos.length === 0 ? (
          <p className="text-xs text-muted">本项目还没有待办事项。</p>
        ) : (
          <div className="space-y-2">
            {data.todos.map((item) => (
              <div key={item.id} className="space-y-1.5">
                <WorkItemRow
                  item={item}
                  busy={updateTodo.isPending}
                  onComplete={(target) =>
                    updateTodo.mutate({ id: target.id, patch: { status: 'done' } })
                  }
                  onPlanToday={(target) =>
                    updateTodo.mutate({
                      id: target.id,
                      patch: { status: 'planned', planned_start_at: planTodayISO() },
                    })
                  }
                />
                <div className="flex flex-wrap items-center gap-2 pl-1 text-xs text-muted">
                  <label htmlFor={`plan-date-${item.id}`}>计划到某天</label>
                  <input
                    id={`plan-date-${item.id}`}
                    className="input w-36 py-1 text-xs"
                    type="date"
                    value={planDates[item.id] ?? ''}
                    onChange={(event) =>
                      setPlanDates((current) => ({ ...current, [item.id]: event.target.value }))
                    }
                  />
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    disabled={updateTodo.isPending || !planDates[item.id]}
                    aria-label={`将「${item.title}」计划到所选日期`}
                    onClick={() => handlePlanDate(item)}
                  >
                    应用计划
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card card-pad space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">仓库快照</h2>
          <button
            type="button"
            className="btn btn-sm"
            disabled={scan.isPending}
            onClick={() => scan.mutate(current.id)}
          >
            {scan.isPending ? '正在扫描…' : '触发扫描'}
          </button>
        </div>
        <p className="break-all text-xs text-muted">
          本地路径：{current.repo_path ?? '未关联'}
        </p>
        {scan.isError ? (
          <p role="alert" className="text-sm text-rose-300">
            {errorMessage(scan.error)}
          </p>
        ) : null}
        {scan.isSuccess ? (
          <p role="status" className="text-xs text-emerald-300">
            扫描完成，健康等级已刷新为 {scan.data.health.level}。
          </p>
        ) : null}

        {!snapshot ? (
          <EmptyState
            title="尚未扫描仓库"
            description="关联本地 Git 仓库路径后触发扫描，只执行只读 Git 命令。"
          />
        ) : (
          <div className="space-y-3">
            {snapshot.state !== 'ok' && snapshot.error ? (
              <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                扫描状态异常：{snapshot.error}
              </p>
            ) : null}
            <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
              <div>
                <dt className="text-xs text-muted">分支</dt>
                <dd className="break-words text-ink">{snapshot.branch ?? '未知'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">upstream</dt>
                <dd className="break-words text-ink">{snapshot.upstream ?? '未配置'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">ahead / behind</dt>
                <dd className="text-ink">
                  {unknownNumber(snapshot.ahead)} / {unknownNumber(snapshot.behind)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted">未提交改动</dt>
                <dd className="text-ink">{unknownNumber(snapshot.dirty_files)} 个文件</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">已暂存</dt>
                <dd className="text-ink">{unknownNumber(snapshot.staged_files)} 个文件</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">未跟踪</dt>
                <dd className="text-ink">{unknownNumber(snapshot.untracked_files)} 个文件</dd>
              </div>
              <div className="col-span-2 md:col-span-3">
                <dt className="text-xs text-muted">最后提交</dt>
                <dd className="break-words text-ink">
                  {snapshot.last_commit_subject ?? '未知'}
                  {snapshot.last_commit_at
                    ? ` · ${formatDateTime(snapshot.last_commit_at)}`
                    : ' · 时间未知'}
                </dd>
              </div>
              <div className="col-span-2 md:col-span-3">
                <dt className="text-xs text-muted">扫描时间</dt>
                <dd className="text-ink">
                  {snapshot.scanned_at ? formatDateTime(snapshot.scanned_at) : '未知'}
                </dd>
              </div>
            </dl>
            {snapshot.github_error ? (
              <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                GitHub：{snapshot.github_error}
              </p>
            ) : snapshot.github && snapshot.github.state === 'ok' ? (
              <div className="rounded-lg border border-edge bg-surface-2/40 p-3">
                <p className="text-xs font-medium text-muted">GitHub</p>
                <dl className="mt-2 grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
                  <div>
                    <dt className="text-xs text-muted">开放 Issue</dt>
                    <dd className="text-ink">{snapshot.github.open_issues ?? 0}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">开放 PR</dt>
                    <dd className="text-ink">
                      {snapshot.github.open_pulls ?? 0}
                      {snapshot.github.oldest_pull_days != null
                        ? ` · 最老 ${snapshot.github.oldest_pull_days} 天`
                        : ''}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">CI</dt>
                    <dd className="text-ink">
                      {snapshot.github.ci_status === 'failure'
                        ? '失败'
                        : snapshot.github.ci_status === 'pending'
                          ? '进行中'
                          : snapshot.github.ci_status === 'success'
                            ? '通过'
                            : '无记录'}
                      {snapshot.github.ci_name ? ` · ${snapshot.github.ci_name}` : ''}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">最近推送</dt>
                    <dd className="text-ink">
                      {snapshot.github.pushed_at
                        ? formatDateTime(snapshot.github.pushed_at)
                        : '未知'}
                    </dd>
                  </div>
                </dl>
              </div>
            ) : null}
            <p className="text-xs text-muted">
              ahead/behind 相对于本地已有远端引用，未自动 fetch，可能受上次 fetch 时间影响。
            </p>
          </div>
        )}
      </section>

      <section className="card card-pad space-y-3">
        <h2 className="text-sm font-semibold text-ink">状态历史</h2>
        {data.status_history.length === 0 ? (
          <p className="text-xs text-muted">还没有状态变更记录。</p>
        ) : (
          <ol className="space-y-2">
            {data.status_history
              .slice()
              .reverse()
              .map((entry) => (
                <li key={entry.id} className="rounded-lg border border-edge bg-surface-2/40 px-3 py-2">
                  <p className="text-xs text-ink">
                    {entry.from_status
                      ? `${PROJECT_STATUS_LABELS[entry.from_status]} → `
                      : '创建 → '}
                    {PROJECT_STATUS_LABELS[entry.to_status]}
                    <span className="ml-2 text-muted">{formatDateTime(entry.changed_at)}</span>
                  </p>
                  {entry.reason ? (
                    <p className="mt-1 text-xs text-muted">原因：{entry.reason}</p>
                  ) : null}
                </li>
              ))}
          </ol>
        )}
      </section>
    </div>
  )
}
