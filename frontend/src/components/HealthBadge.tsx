import type { HealthLevel } from '../api/types'
import { HEALTH_CLASSES, HEALTH_ICONS, HEALTH_LABELS } from '../lib/format'

interface HealthBadgeProps {
  level: HealthLevel
  className?: string
}

export function HealthBadge({ level, className }: HealthBadgeProps) {
  const label = HEALTH_LABELS[level]
  return (
    <span
      role="status"
      aria-label={`健康状态：${label}`}
      className={`chip ${HEALTH_CLASSES[level]} ${className ?? ''}`}
    >
      <span aria-hidden="true">{HEALTH_ICONS[level]}</span>
      <span>{label}</span>
    </span>
  )
}
