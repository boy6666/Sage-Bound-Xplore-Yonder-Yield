import { useState, type FormEvent } from 'react'
import type {
  Course,
  ItemType,
  Priority,
  Project,
  WorkItem,
  WorkItemInput,
  WorkItemStatus,
} from '../api/types'
import {
  useCourses,
  useCreateWorkItem,
  useDeleteWorkItem,
  useProjects,
  useUpdateWorkItem,
  useWorkItems,
} from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { Field } from '../components/Field'
import { Modal } from '../components/Modal'
import { WorkItemRow } from '../components/WorkItemRow'
import { isoToLocalInput, localInputToISO, planTodayISO } from '../lib/date'
import {
  ITEM_TYPE_LABELS,
  PRIORITY_LABELS,
  PRIORITY_ORDER,
  SOURCE_LABELS,
  SOURCE_OPTIONS,
  WORK_ITEM_STATUS_LABELS,
  WORK_ITEM_STATUS_OPTIONS,
  errorMessage,
} from '../lib/format'
import { useSearchParams } from 'react-router-dom'

interface WorkItemFormProps {
  initial: WorkItem | null
  courses: Course[]
  projects: Project[]
  submitting: boolean
  serverError: unknown
  onSubmit: (input: WorkItemInput) => void
  onCancel: () => void
}

function WorkItemForm({
  initial,
  courses,
  projects,
  submitting,
  serverError,
  onSubmit,
  onCancel,
}: WorkItemFormProps) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [notes, setNotes] = useState(initial?.notes ?? '')
  const [itemType, setItemType] = useState<ItemType>(initial?.item_type ?? 'task')
  const [priority, setPriority] = useState<Priority>(initial?.priority ?? 'normal')
  const [status, setStatus] = useState<WorkItemStatus>(initial?.status ?? 'inbox')
  const [dueAt, setDueAt] = useState(isoToLocalInput(initial?.due_at))
  const [plannedStart, setPlannedStart] = useState(
    isoToLocalInput(initial?.planned_start_at),
  )
  const [plannedEnd, setPlannedEnd] = useState(isoToLocalInput(initial?.planned_end_at))
  const [estimate, setEstimate] = useState(
    initial?.estimate_minutes !== null && initial?.estimate_minutes !== undefined
      ? String(initial.estimate_minutes)
      : '',
  )
  const [courseId, setCourseId] = useState(initial?.course_id ?? '')
  const [projectId, setProjectId] = useState(initial?.project_id ?? '')
  const [isBlocked, setIsBlocked] = useState(Boolean(initial?.blocked_reason))
  const [blockedReason, setBlockedReason] = useState(initial?.blocked_reason ?? '')
  const [formError, setFormError] = useState<string | null>(null)
  const externalLocked = initial !== null && initial.source_type !== 'manual'

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!title.trim()) {
      setFormError('标题不能为空。')
      return
    }
    if (isBlocked && !blockedReason.trim()) {
      setFormError('阻塞状态必须填写受阻原因。')
      return
    }
    if (plannedStart && plannedEnd) {
      const start = new Date(plannedStart).getTime()
      const end = new Date(plannedEnd).getTime()
      if (Number.isFinite(start) && Number.isFinite(end) && end <= start) {
        setFormError('计划结束时间必须晚于计划开始时间。')
        return
      }
    }
    setFormError(null)

    const estimateValue = estimate.trim() === '' ? null : Number(estimate)
    onSubmit({
      title: title.trim(),
      notes: notes.trim() === '' ? null : notes.trim(),
      item_type: itemType,
      priority,
      status,
      due_at: localInputToISO(dueAt),
      planned_start_at: localInputToISO(plannedStart),
      planned_end_at: localInputToISO(plannedEnd),
      estimate_minutes:
        estimateValue === null || Number.isNaN(estimateValue) ? null : estimateValue,
      blocked_reason: isBlocked ? blockedReason.trim() : null,
      course_id: courseId || null,
      project_id: projectId || null,
    })
  }

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      <Field
        label="标题"
        htmlFor="item-title"
        required
        hint={externalLocked ? '来源平台同步的事项标题不可在本地改写。' : undefined}
      >
        <input
          id="item-title"
          className="input"
          value={title}
          disabled={externalLocked}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="例如：操作系统实验二"
        />
      </Field>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="事项类型" htmlFor="item-type">
          <select
            id="item-type"
            className="input"
            value={itemType}
            onChange={(event) => setItemType(event.target.value as ItemType)}
          >
            {(Object.keys(ITEM_TYPE_LABELS) as ItemType[]).map((type) => (
              <option key={type} value={type}>
                {ITEM_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="优先级" htmlFor="item-priority">
          <select
            id="item-priority"
            className="input"
            value={priority}
            onChange={(event) => setPriority(event.target.value as Priority)}
          >
            {PRIORITY_ORDER.map((value) => (
              <option key={value} value={value}>
                {PRIORITY_LABELS[value]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="执行状态" htmlFor="item-status">
          <select
            id="item-status"
            className="input"
            value={status}
            onChange={(event) => setStatus(event.target.value as WorkItemStatus)}
          >
            {WORK_ITEM_STATUS_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {WORK_ITEM_STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="预计分钟" htmlFor="item-estimate">
          <input
            id="item-estimate"
            className="input"
            type="number"
            min={0}
            value={estimate}
            onChange={(event) => setEstimate(event.target.value)}
          />
        </Field>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="截止时间" htmlFor="item-due" hint="到分钟，与计划执行时间区分。">
          <input
            id="item-due"
            className="input"
            type="datetime-local"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
          />
        </Field>
        <Field label="计划开始" htmlFor="item-planned-start">
          <input
            id="item-planned-start"
            className="input"
            type="datetime-local"
            value={plannedStart}
            onChange={(event) => setPlannedStart(event.target.value)}
          />
        </Field>
        <Field label="计划结束" htmlFor="item-planned-end">
          <input
            id="item-planned-end"
            className="input"
            type="datetime-local"
            value={plannedEnd}
            onChange={(event) => setPlannedEnd(event.target.value)}
          />
        </Field>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          label="课程"
          htmlFor="item-course"
          hint={externalLocked ? '课程归属请通过课程身份映射调整。' : undefined}
        >
          <select
            id="item-course"
            className="input"
            value={courseId}
            disabled={externalLocked}
            onChange={(event) => setCourseId(event.target.value)}
          >
            <option value="">不关联课程</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="项目" htmlFor="item-project">
          <select
            id="item-project"
            className="input"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
          >
            <option value="">不关联项目</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="备注" htmlFor="item-notes">
        <textarea
          id="item-notes"
          className="input min-h-20"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="补充上下文、下一步或注意事项"
        />
      </Field>

      <label
        className="flex items-center gap-2 text-sm text-muted"
        htmlFor="item-blocked-toggle"
      >
        <input
          id="item-blocked-toggle"
          type="checkbox"
          className="h-4 w-4 rounded border-edge bg-bg"
          checked={isBlocked}
          onChange={(event) => setIsBlocked(event.target.checked)}
        />
        标记为受阻
      </label>

      {isBlocked ? (
        <Field label="受阻原因" htmlFor="item-blocked" required>
          <textarea
            id="item-blocked"
            className="input min-h-16"
            value={blockedReason}
            onChange={(event) => setBlockedReason(event.target.value)}
            placeholder="说明具体阻塞问题"
          />
        </Field>
      ) : null}

      {formError ? (
        <p role="alert" className="text-sm text-rose-300">
          {formError}
        </p>
      ) : null}

      {serverError ? (
        <p role="alert" className="text-sm text-rose-300">
          {errorMessage(serverError)}
        </p>
      ) : null}

      <div className="flex flex-wrap justify-end gap-2 pt-1">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          取消
        </button>
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? '正在保存…' : '保存事项'}
        </button>
      </div>
    </form>
  )
}

export function Inbox() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = (searchParams.get('status') ?? '') as WorkItemStatus | ''
  const sourceType = (searchParams.get('source_type') ?? '') as WorkItem['source_type'] | ''
  const courseId = searchParams.get('course_id') ?? ''
  const projectId = searchParams.get('project_id') ?? ''
  const q = searchParams.get('q') ?? ''

  const itemsQuery = useWorkItems({
    status,
    source_type: sourceType,
    course_id: courseId,
    project_id: projectId,
    q,
    limit: 100,
  })
  const coursesQuery = useCourses()
  const projectsQuery = useProjects()
  const createItem = useCreateWorkItem()
  const updateItem = useUpdateWorkItem()
  const deleteItem = useDeleteWorkItem()

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<WorkItem | null>(null)

  const setFilter = (key: string, value: string): void => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearchParams(next, { replace: true })
  }

  const openCreate = (): void => {
    setEditing(null)
    setFormOpen(true)
  }

  const openEdit = (item: WorkItem): void => {
    setEditing(item)
    setFormOpen(true)
  }

  const closeForm = (): void => {
    setFormOpen(false)
    setEditing(null)
    createItem.reset()
    updateItem.reset()
  }

  const handleSubmit = (input: WorkItemInput): void => {
    if (editing) {
      updateItem.mutate(
        { id: editing.id, patch: input },
        { onSuccess: () => closeForm() },
      )
    } else {
      createItem.mutate(input, { onSuccess: () => closeForm() })
    }
  }

  const handleDelete = (item: WorkItem): void => {
    if (window.confirm(`确定删除「${item.title}」吗？该操作不可撤销。`)) {
      deleteItem.mutate(item.id)
    }
  }

  const items = (itemsQuery.data?.items ?? []).filter((item) => {
    if (status) return true
    return item.status !== 'done' && item.status !== 'dismissed'
  })

  const actionError = createItem.error ?? updateItem.error ?? deleteItem.error

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">统一收件箱</h1>
          <p className="text-sm text-muted">
            汇总学习平台、项目与手动事项；筛选条件会保留在地址栏。
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          新建事项
        </button>
      </header>

      <section className="card card-pad space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="来源" htmlFor="filter-source">
            <select
              id="filter-source"
              className="input"
              value={sourceType}
              onChange={(event) => setFilter('source_type', event.target.value)}
            >
              <option value="">全部来源</option>
              {SOURCE_OPTIONS.map((source) => (
                <option key={source} value={source}>
                  {SOURCE_LABELS[source]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="课程" htmlFor="filter-course">
            <select
              id="filter-course"
              className="input"
              value={courseId}
              onChange={(event) => setFilter('course_id', event.target.value)}
            >
              <option value="">全部课程</option>
              {(coursesQuery.data?.items ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {course.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="项目" htmlFor="filter-project">
            <select
              id="filter-project"
              className="input"
              value={projectId}
              onChange={(event) => setFilter('project_id', event.target.value)}
            >
              <option value="">全部项目</option>
              {(projectsQuery.data?.items ?? []).map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="状态" htmlFor="filter-status">
            <select
              id="filter-status"
              className="input"
              value={status}
              onChange={(event) => setFilter('status', event.target.value)}
            >
              <option value="">未处理</option>
              {WORK_ITEM_STATUS_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {WORK_ITEM_STATUS_LABELS[value]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="搜索" htmlFor="filter-q">
            <input
              id="filter-q"
              className="input"
              value={q}
              placeholder="按标题模糊搜索"
              onChange={(event) => setFilter('q', event.target.value)}
            />
          </Field>
        </div>
      </section>

      {actionError ? <ErrorState error={actionError} title="事项操作失败" /> : null}

      {itemsQuery.isPending ? (
        <div className="space-y-2" aria-busy="true">
          <div className="h-20 animate-pulse rounded-card bg-surface" />
          <div className="h-20 animate-pulse rounded-card bg-surface" />
          <p className="text-xs text-muted">正在加载事项…</p>
        </div>
      ) : itemsQuery.isError ? (
        <ErrorState
          error={itemsQuery.error}
          title="收件箱加载失败"
          onRetry={() => void itemsQuery.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="没有符合条件的事项"
          description="调整筛选条件，或新建一个手动事项。学习平台事项会在同步后出现在这里。"
          action={
            <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
              新建事项
            </button>
          }
        />
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted">共 {items.length} 项</p>
          {items.map((item) => (
            <WorkItemRow
              key={item.id}
              item={item}
              busy={updateItem.isPending || deleteItem.isPending}
              onComplete={(target) =>
                updateItem.mutate({ id: target.id, patch: { status: 'done' } })
              }
              onPlanToday={(target) =>
                updateItem.mutate({
                  id: target.id,
                  patch: { status: 'planned', planned_start_at: planTodayISO() },
                })
              }
              onPriorityChange={(target, priority) =>
                updateItem.mutate({ id: target.id, patch: { priority } })
              }
              onEdit={openEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <Modal
        open={formOpen}
        title={editing ? '编辑事项' : '新建事项'}
        description="截止时间与计划执行时间是两个独立字段。来源平台字段不可在本地改写。"
        onClose={closeForm}
        widthClass="max-w-2xl"
      >
        <WorkItemForm
          key={editing?.id ?? 'new'}
          initial={editing}
          courses={coursesQuery.data?.items ?? []}
          projects={projectsQuery.data?.items ?? []}
          submitting={createItem.isPending || updateItem.isPending}
          serverError={createItem.error ?? updateItem.error}
          onSubmit={handleSubmit}
          onCancel={closeForm}
        />
      </Modal>
    </div>
  )
}
