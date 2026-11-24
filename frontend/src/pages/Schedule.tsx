import { Link, useSearchParams } from 'react-router-dom'
import { useSchedule } from '../api/queries'
import { ErrorState } from '../components/ErrorState'
import { ScheduleGrid } from '../components/ScheduleGrid'
import { formatDate } from '../lib/date'

export function Schedule() {
  const [searchParams, setSearchParams] = useSearchParams()
  const weekParam = searchParams.get('week')
  const parsedWeek = weekParam ? Number(weekParam) : undefined
  const week = Number.isFinite(parsedWeek) ? parsedWeek : undefined

  const scheduleQuery = useSchedule(week)

  const goToWeek = (next: number): void => {
    const params = new URLSearchParams(searchParams)
    if (next > 0) params.set('week', String(next))
    else params.delete('week')
    setSearchParams(params, { replace: true })
  }

  if (scheduleQuery.isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        <div className="h-8 w-40 animate-pulse rounded bg-surface-2" />
        <div className="h-64 animate-pulse rounded-card bg-surface" />
        <p className="text-xs text-muted">正在加载课程表…</p>
      </div>
    )
  }

  if (scheduleQuery.isError) {
    return (
      <ErrorState
        error={scheduleQuery.error}
        title="课程表加载失败"
        onRetry={() => void scheduleQuery.refetch()}
      />
    )
  }

  const data = scheduleQuery.data
  const activeWeek = data.current_week

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">课程表</h1>
          <p className="text-sm text-muted">
            第 {activeWeek} 教学周
            {data.term_start_date
              ? ` · 第一教学周周一 ${formatDate(data.term_start_date)}`
              : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn btn-sm"
            disabled={activeWeek <= 1}
            onClick={() => goToWeek(activeWeek - 1)}
          >
            上一周
          </button>
          <button type="button" className="btn btn-sm" onClick={() => goToWeek(activeWeek)}>
            本周
          </button>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => goToWeek(activeWeek + 1)}
          >
            下一周
          </button>
        </div>
      </header>

      {data.missing_term_start ? (
        <div
          role="status"
          className="card card-pad flex flex-wrap items-center justify-between gap-2 border-amber-500/40 bg-amber-500/10"
        >
          <p className="text-sm text-amber-100">
            尚未确认第一教学周周一，无法准确推算课程周次。
          </p>
          <Link className="btn btn-sm" to="/settings">
            去设置
          </Link>
        </div>
      ) : null}

      <ScheduleGrid entries={data.entries} items={data.items} />

      <p className="text-xs text-muted">
        课程条目来自教务课程表，不是待办；下方“本周任务”是按计划开始时间或截止时间落到本周的事项。
        点击课程可查看该课程的跨平台待办。
      </p>
    </div>
  )
}
