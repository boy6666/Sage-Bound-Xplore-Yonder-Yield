import { Link } from 'react-router-dom'
import type { Priority, WorkItem } from '../api/types'
import {
  useBootstrap,
  useToday,
  useUpdateWorkItem,
} from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { WorkItemRow } from '../components/WorkItemRow'
import {
  formatDateLong,
  planTodayISO,
  todayInTimeZone,
  weekdayLabel,
} from '../lib/date'
import { HEALTH_LABELS } from '../lib/format'

interface SectionProps {
  title: string
  hint?: string
  items: WorkItem[]
  busy: boolean
  onComplete: (item: WorkItem) => void
  onPlanToday: (item: WorkItem) => void
  onPriorityChange: (item: WorkItem, priority: Priority) => void
  emptyText: string
  accentClass?: string
}

function ItemSection({
  title,
  hint,
  items,
  busy,
  onComplete,
  onPlanToday,
  onPriorityChange,
  emptyText,
  accentClass,
}: SectionProps) {
  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className={`text-sm font-semibold ${accentClass ?? 'text-ink'}`}>
          {title}
          <span className="ml-1.5 text-xs font-normal text-muted">{items.length}</span>
        </h2>
        {hint ? <p className="text-xs text-muted">{hint}</p> : null}
      </div>
      {items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-edge px-3 py-4 text-xs text-muted">
          {emptyText}
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <WorkItemRow
              key={item.id}
              item={item}
              busy={busy}
              onComplete={onComplete}
              onPlanToday={onPlanToday}
              onPriorityChange={onPriorityChange}
            />
          ))}
        </div>
      )}
    </section>
  )
}

export function Today() {
  const bootstrap = useBootstrap()
  const timezone = bootstrap.data?.timezone
  const date = bootstrap.data?.today ?? todayInTimeZone(timezone)
  const today = useToday(date)
  const update = useUpdateWorkItem()

  const handleComplete = (item: WorkItem): void => {
    update.mutate({ id: item.id, patch: { status: 'done' } })
  }

  const handlePlanToday = (item: WorkItem): void => {
    update.mutate({
      id: item.id,
      patch: { status: 'planned', planned_start_at: planTodayISO() },
    })
  }

  const handlePriorityChange = (item: WorkItem, priority: Priority): void => {
    update.mutate({ id: item.id, patch: { priority } })
  }

  if (today.isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        <div className="h-6 w-40 animate-pulse rounded bg-surface-2" />
        <div className="grid gap-3 md:grid-cols-2">
          <div className="h-28 animate-pulse rounded-card bg-surface" />
          <div className="h-28 animate-pulse rounded-card bg-surface" />
        </div>
        <p className="text-xs text-muted">正在加载今日数据…</p>
      </div>
    )
  }

  if (today.isError) {
    return (
      <ErrorState
        error={today.error}
        title="今日数据加载失败"
        onRetry={() => void today.refetch()}
      />
    )
  }

  const data = today.data
  const parsedWeekday = new Date(`${data.date}T00:00:00`).getDay()
  const weekdayNumber = parsedWeekday === 0 ? 7 : parsedWeekday
  const totalItems =
    data.overdue.length +
    data.today_planned.length +
    data.upcoming_unplanned.length +
    data.blocked.length

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted">Today</p>
          <h1 className="text-xl font-semibold text-ink">
            {formatDateLong(data.date, data.timezone)}
          </h1>
          <p className="text-xs text-muted">{data.timezone}</p>
        </div>
        <Link className="btn btn-sm" to="/inbox">
          打开收件箱
        </Link>
      </header>

      {data.data_warnings.length > 0 ? (
        <div
          role="status"
          className="card card-pad space-y-1 border-amber-500/40 bg-amber-500/10"
        >
          <p className="text-sm font-semibold text-amber-200">数据提示</p>
          <ul className="list-disc space-y-1 pl-5 text-xs text-amber-100/80">
            {data.data_warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {update.isError ? (
        <ErrorState error={update.error} title="更新事项失败" />
      ) : null}

      <div className="grid gap-3 lg:grid-cols-2">
        <section className="card card-pad space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">今日课程</h2>
            <span className="text-xs text-muted">{data.classes_today.length} 节</span>
          </div>
          {data.classes_today.length === 0 ? (
            <p className="text-xs text-muted">
              今天没有课程安排。如果课程表尚未同步，可前往同步中心检查连接。
            </p>
          ) : (
            <ul className="space-y-2">
              {data.classes_today.map((entry) => (
                <li
                  key={`${entry.course_id}-${entry.start_time}`}
                  className="rounded-lg border border-edge bg-surface-2/50 p-2.5"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <Link
                      to={`/courses/${entry.course_id}`}
                      className="text-sm font-medium text-ink hover:text-accent"
                    >
                      {entry.course_name}
                    </Link>
                    <span className="text-xs text-muted">
                      {entry.start_time}-{entry.end_time}
                    </span>
                  </div>
                  <p className="text-xs text-muted">
                    {entry.location ?? '地点未设置'}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    该课程未完成待办：
                    <Link
                      to={`/inbox?course_id=${entry.course_id}`}
                      className="text-accent hover:underline"
                    >
                      {entry.open_todos} 项
                    </Link>
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-pad space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">项目风险</h2>
            <span className="text-xs text-muted">{data.project_risks.length} 项</span>
          </div>
          {data.project_risks.length === 0 ? (
            <p className="text-xs text-muted">当前没有红色项目风险。</p>
          ) : (
            <ul className="space-y-2">
              {data.project_risks.map((risk) => (
                <li key={risk.project_id} className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Link
                      to={`/projects/${risk.project_id}`}
                      className="text-sm font-medium text-rose-100 hover:underline"
                    >
                      {risk.name}
                    </Link>
                    <span className="chip bg-rose-500/20 text-rose-200 ring-rose-400/40">
                      {HEALTH_LABELS[risk.level]}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-rose-100/80">{risk.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {totalItems === 0 ? (
        <EmptyState
          title="今天没有待处理事项"
          description="可以到收件箱计划新的事项，或检查同步状态确认外部数据是否最新。"
          action={
            <Link className="btn btn-primary btn-sm" to="/inbox">
              前往收件箱
            </Link>
          }
        />
      ) : (
        <div className="space-y-6">
          <ItemSection
            title="逾期"
            hint="截止日期早于今天"
            items={data.overdue}
            busy={update.isPending}
            onComplete={handleComplete}
            onPlanToday={handlePlanToday}
            onPriorityChange={handlePriorityChange}
            emptyText="没有逾期事项。"
            accentClass="text-rose-300"
          />
          <ItemSection
            title="今日计划"
            hint="已安排在今天"
            items={data.today_planned}
            busy={update.isPending}
            onComplete={handleComplete}
            onPlanToday={handlePlanToday}
            onPriorityChange={handlePriorityChange}
            emptyText="今天还没有计划事项。"
            accentClass="text-sky-300"
          />
          <ItemSection
            title="即将截止未安排"
            hint="在临近截止窗口内且尚未安排时间"
            items={data.upcoming_unplanned}
            busy={update.isPending}
            onComplete={handleComplete}
            onPlanToday={handlePlanToday}
            onPriorityChange={handlePriorityChange}
            emptyText="没有临近截止但未安排的事项。"
          />
          <ItemSection
            title="受阻"
            hint="已填写受阻原因"
            items={data.blocked}
            busy={update.isPending}
            onComplete={handleComplete}
            onPlanToday={handlePlanToday}
            onPriorityChange={handlePriorityChange}
            emptyText="没有受阻事项。"
            accentClass="text-amber-300"
          />
        </div>
      )}

      {data.classes_today.length > 0 ? (
        <p className="text-xs text-muted">
          今日课程按第一教学周推算，今天为{weekdayLabel(weekdayNumber)}。
        </p>
      ) : null}
    </div>
  )
}
