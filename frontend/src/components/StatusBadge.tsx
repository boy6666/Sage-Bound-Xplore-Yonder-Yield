import type { ProjectStatus, WorkItemStatus } from '../api/types'
import {
  PROJECT_STATUS_CLASSES,
  PROJECT_STATUS_LABELS,
  WORK_ITEM_STATUS_CLASSES,
  WORK_ITEM_STATUS_LABELS,
} from '../lib/format'

interface StatusBadgeProps {
  status: WorkItemStatus | ProjectStatus
  kind?: 'work-item' | 'project'
  reason?: string | null
  className?: string
}

export function StatusBadge({
  status,
  kind = 'work-item',
  reason,
  className,
}: StatusBadgeProps) {
  const isProject = kind === 'project'
  const label = isProject
    ? PROJECT_STATUS_LABELS[status as ProjectStatus]
    : WORK_ITEM_STATUS_LABELS[status as WorkItemStatus]
  const tone = isProject
    ? PROJECT_STATUS_CLASSES[status as ProjectStatus]
    : WORK_ITEM_STATUS_CLASSES[status as WorkItemStatus]

  return (
    <span className={`inline-flex min-w-0 flex-wrap items-center gap-1.5 ${className ?? ''}`}>
      <span className={`chip ${tone}`}>{label}</span>
      {isProject && reason ? (
        <span className="min-w-0 break-words text-xs text-muted">{reason}</span>
      ) : null}
    </span>
  )
}
