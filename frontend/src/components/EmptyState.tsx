import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-10 text-center">
      {icon ? (
        <div aria-hidden="true" className="text-2xl text-muted">
          {icon}
        </div>
      ) : null}
      <div className="space-y-1">
        <p className="text-base font-semibold text-ink">{title}</p>
        {description ? <p className="max-w-md text-sm text-muted">{description}</p> : null}
      </div>
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  )
}
