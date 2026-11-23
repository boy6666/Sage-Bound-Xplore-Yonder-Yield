import { Link } from 'react-router-dom'
import type { Project } from '../api/types'
import { formatDateTime } from '../lib/date'
import { HEALTH_DESCRIPTIONS } from '../lib/format'
import { HealthBadge } from './HealthBadge'
import { StatusBadge } from './StatusBadge'

interface ProjectCardProps {
  project: Project
}

export function ProjectCard({ project }: ProjectCardProps) {
  const total = project.milestones_total
  const done = project.milestones_done
  const percent = total === 0 ? 0 : Math.round((done / total) * 100)

  return (
    <article className="card card-pad flex min-w-0 flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <h3 className="truncate text-base font-semibold text-ink">
            <Link className="hover:text-accent" to={`/projects/${project.id}`}>
              {project.name}
            </Link>
          </h3>
          {project.description ? (
            <p className="line-clamp-2 text-sm text-muted">{project.description}</p>
          ) : null}
        </div>
        <HealthBadge level={project.health.level} />
      </div>

      <StatusBadge kind="project" status={project.status} reason={project.status_reason} />

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted">项目待办</dt>
          <dd className="font-medium text-ink">{project.open_todos} 项未完成</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">里程碑</dt>
          <dd className="font-medium text-ink">
            {done}/{total} 个完成
          </dd>
        </div>
      </dl>

      <div className="space-y-1">
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          aria-label={`${project.name} 里程碑进度`}
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full bg-accent"
            style={{ width: `${percent}%` }}
          />
        </div>
        <p className="text-xs text-muted">里程碑进度 {percent}%</p>
      </div>

      <div className="space-y-1">
        <p className="text-xs text-muted">下一步行动</p>
        <p className="text-sm text-ink">
          {project.next_action ? project.next_action : '尚未设置下一步行动'}
        </p>
      </div>

      {project.status_changed_at ? (
        <p className="text-xs text-muted">
          状态更新于 {formatDateTime(project.status_changed_at)}
        </p>
      ) : null}

      <details className="rounded-lg border border-edge bg-surface-2/40 p-3">
        <summary className="cursor-pointer text-xs font-medium text-muted">
          健康原因（{project.health.reasons.length}）
        </summary>
        <div className="mt-2 space-y-2">
          <p className="text-xs text-muted">{HEALTH_DESCRIPTIONS[project.health.level]}</p>
          {project.health.reasons.length === 0 ? (
            <p className="text-xs text-muted">当前没有返回具体的健康原因。</p>
          ) : (
            <ul className="space-y-1.5">
              {project.health.reasons.map((reason) => (
                <li key={`${reason.code}-${reason.label}`} className="text-xs">
                  <span className="font-medium text-ink">{reason.label}</span>
                  {reason.detail ? (
                    <span className="text-muted"> — {reason.detail}</span>
                  ) : null}
                  {reason.action ? (
                    <span className="ml-1 text-muted">（定位：{reason.action}）</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>
    </article>
  )
}
