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
import { isoToLocalInput, localInputToISO } from '../lib/date'
import {
  ITEM_TYPE_LABELS,
  PRIORITY_LABELS,
  PRIORITY_ORDER,
  WORK_ITEM_STATUS_LABELS,
  WORK_ITEM_STATUS_OPTIONS,
  errorMessage,
} from '../lib/format'
import { Field } from './Field'

export interface WorkItemFormProps {
  initial?: Partial<WorkItem> | null
  courses: Course[]
  projects: Project[]
  submitting: boolean
  serverError: unknown
  onSubmit: (input: WorkItemInput) => void
  onCancel: () => void
  submitLabel?: string
}

export function WorkItemForm({
  initial,
  courses,
  projects,
  submitting,
  serverError,
  onSubmit,
  onCancel,
  submitLabel = '保存事项',
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
  const externalLocked = Boolean(
    initial?.source_type && initial.source_type !== 'manual',
  )

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
        <Field label="计划开始" htmlFor="item-planned-start" hint="填写后会出现在日程表。">
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
          {submitting ? '正在保存…' : submitLabel}
        </button>
      </div>
    </form>
  )
}
