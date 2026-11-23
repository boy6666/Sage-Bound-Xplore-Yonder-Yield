import { Link } from 'react-router-dom'
import type { Priority, WorkItem } from '../api/types'
import { formatDate, formatDateTime, localDateOf, todayInTimeZone } from '../lib/date'
import {
  ITEM_TYPE_LABELS,
  PRIORITY_CLASSES,
  PRIORITY_LABELS,
  PRIORITY_ORDER,
  SOURCE_LABELS,
} from '../lib/format'
import { StatusBadge } from './StatusBadge'

interface WorkItemRowProps {
  item: WorkItem
  onComplete?: (item: WorkItem) => void
  onPlanToday?: (item: WorkItem) => void
  onPriorityChange?: (item: WorkItem, priority: Priority) => void
  onEdit?: (item: WorkItem) => void
  onDelete?: (item: WorkItem) => void
  busy?: boolean
}

export function WorkItemRow({
  item,
  onComplete,
  onPlanToday,
  onPriorityChange,
  onEdit,
  onDelete,
  busy = false,
}: WorkItemRowProps) {
  const isOverdue =
    Boolean(item.due_at) &&
    item.status !== 'done' &&
    item.status !== 'dismissed' &&
    localDateOf(item.due_at as string) < todayInTimeZone()

  return (
    <article
      className={`card card-pad flex min-w-0 flex-col gap-3 ${
        isOverdue ? 'border-rose-500/40' : ''
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1 space-y-1">
          <h3 className="text-sm font-semibold leading-5 text-ink break-words">
            {item.title}
          </h3>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="chip bg-surface-2 text-muted ring-edge">
              {SOURCE_LABELS[item.source_type]}
            </span>
            <span className="chip bg-surface-2 text-muted ring-edge">
              {ITEM_TYPE_LABELS[item.item_type]}
            </span>
            <StatusBadge status={item.status} />
            <span className={`chip ${PRIORITY_CLASSES[item.priority]}`}>
              {PRIORITY_LABELS[item.priority]}优先级
            </span>
            {item.needs_review ? (
              <span className="chip bg-amber-500/10 text-amber-300 ring-amber-500/30">
                来源待核实
              </span>
            ) : null}
          </div>
        </div>
        {onPriorityChange ? (
          <label className="flex items-center gap-1 text-xs text-muted">
            <span className="sr-only">优先级</span>
            <select
              aria-label={`设置「${item.title}」优先级`}
              className="input w-auto py-1 text-xs"
              value={item.priority}
              disabled={busy}
              onChange={(event) =>
                onPriorityChange(item, event.target.value as Priority)
              }
            >
              {PRIORITY_ORDER.map((priority) => (
                <option key={priority} value={priority}>
                  {PRIORITY_LABELS[priority]}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <div className="grid gap-1 text-xs text-muted sm:grid-cols-2">
        <p>
          截止：
          <span className={isOverdue ? 'font-semibold text-rose-300' : 'text-ink'}>
            {item.due_at ? formatDateTime(item.due_at) : '无'}
          </span>
          {isOverdue ? <span className="ml-1 text-rose-300">已逾期</span> : null}
        </p>
        <p>
          计划：
          <span className="text-ink">
            {item.planned_start_at
              ? formatDateTime(item.planned_start_at)
              : item.planned_end_at
                ? formatDate(item.planned_end_at)
                : '未安排'}
          </span>
        </p>
        {item.course_name ? (
          <p>
            课程：
            {item.course_id ? (
              <Link
                to={`/courses/${item.course_id}`}
                className="text-accent hover:underline"
              >
                {item.course_name}
              </Link>
            ) : (
              <span className="text-ink">{item.course_name}</span>
            )}
          </p>
        ) : null}
        {item.project_name ? (
          <p>
            项目：
            {item.project_id ? (
              <Link
                to={`/projects/${item.project_id}`}
                className="text-accent hover:underline"
              >
                {item.project_name}
              </Link>
            ) : (
              <span className="text-ink">{item.project_name}</span>
            )}
          </p>
        ) : null}
        {item.estimate_minutes !== null ? (
          <p>
            预计：<span className="text-ink">{item.estimate_minutes} 分钟</span>
          </p>
        ) : null}
        {item.external_status ? (
          <p>
            平台状态：<span className="text-ink">{item.external_status}</span>
          </p>
        ) : null}
      </div>

      {item.notes ? (
        <p className="whitespace-pre-wrap break-words rounded-lg bg-surface-2/50 px-3 py-2 text-xs text-muted">
          {item.notes}
        </p>
      ) : null}

      {item.blocked_reason ? (
        <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          受阻原因：{item.blocked_reason}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        {item.source_url ? (
          <a
            className="btn btn-sm btn-ghost"
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`在新窗口打开「${item.title}」来源`}
          >
            打开原平台
          </a>
        ) : null}
        {onComplete && item.status !== 'done' ? (
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy}
            aria-label={`完成「${item.title}」`}
            onClick={() => onComplete(item)}
          >
            完成
          </button>
        ) : null}
        {onPlanToday && item.status !== 'done' ? (
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy}
            aria-label={`计划今天「${item.title}」`}
            onClick={() => onPlanToday(item)}
          >
            计划今天
          </button>
        ) : null}
        {onEdit ? (
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            aria-label={`编辑「${item.title}」`}
            onClick={() => onEdit(item)}
          >
            编辑
          </button>
        ) : null}
        {onDelete ? (
          <button
            type="button"
            className="btn btn-sm btn-danger"
            disabled={busy}
            aria-label={`删除「${item.title}」`}
            onClick={() => onDelete(item)}
          >
            删除
          </button>
        ) : null}
      </div>
    </article>
  )
}
