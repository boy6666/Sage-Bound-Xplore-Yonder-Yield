import { Link } from 'react-router-dom'
import type { ScheduleEntry, ScheduleItem } from '../api/types'
import { WEEKDAY_LABELS } from '../lib/date'
import { EmptyState } from './EmptyState'

interface ScheduleGridProps {
  entries: ScheduleEntry[]
  items?: ScheduleItem[]
  emptyHint?: string
}

function ItemBadge({ item }: { item: ScheduleItem }) {
  const tone =
    item.kind === 'due'
      ? 'border-amber-500/30 bg-amber-500/10 text-amber-100'
      : 'border-violet-500/30 bg-violet-500/10 text-violet-100'
  const body = (
    <>
      <div className="flex items-baseline justify-between gap-2">
        <span className="min-w-0 truncate font-medium">{item.title}</span>
        <span className="shrink-0 text-[10px] opacity-80">{item.time_label}</span>
      </div>
      {item.course_name ? (
        <span className="block truncate text-[10px] opacity-70">{item.course_name}</span>
      ) : null}
    </>
  )
  const className = `block min-w-0 rounded-md border p-1.5 text-[11px] leading-4 ${tone}`

  if (item.course_id) {
    return (
      <Link to={`/courses/${item.course_id}`} className={`${className} hover:brightness-125`}>
        {body}
      </Link>
    )
  }
  return <div className={className}>{body}</div>
}

export function ScheduleGrid({ entries, items = [], emptyHint }: ScheduleGridProps) {
  if (entries.length === 0 && items.length === 0) {
    return (
      <EmptyState
        title="本周没有课程"
        description={emptyHint ?? '如果教务课程表尚未同步，请到同步中心检查连接状态。'}
      />
    )
  }

  const slots = Array.from(
    new Set(entries.map((entry) => `${entry.start_time}-${entry.end_time}`)),
  ).sort((a, b) => a.localeCompare(b))

  return (
    <>
      {slots.length > 0 ? (
        <div className="hidden overflow-hidden rounded-card border border-edge bg-surface md:block">
          <div className="grid grid-cols-[4.5rem_repeat(7,minmax(0,1fr))] border-b border-edge bg-surface-2/60 text-xs font-medium text-muted">
            <div className="px-2 py-2">时间</div>
            {WEEKDAY_LABELS.map((label) => (
              <div key={label} className="px-1 py-2 text-center">
                {label}
              </div>
            ))}
          </div>
          {slots.map((slot) => {
            const [start, end] = slot.split('-')
            const rowEntries = entries.filter(
              (entry) => `${entry.start_time}-${entry.end_time}` === slot,
            )
            return (
              <div
                key={slot}
                className="grid grid-cols-[4.5rem_repeat(7,minmax(0,1fr))] border-b border-edge/60 last:border-b-0"
              >
                <div className="space-y-0.5 px-2 py-2 text-[11px] leading-4 text-muted">
                  <p>{start}</p>
                  <p>{end}</p>
                </div>
                {Array.from({ length: 7 }, (_, index) => {
                  const weekday = index + 1
                  const cell = rowEntries.filter((entry) => entry.weekday === weekday)
                  return (
                    <div
                      key={weekday}
                      className="min-w-0 border-l border-edge/60 p-1 align-top"
                    >
                      {cell.map((entry) => (
                        <Link
                          key={entry.id}
                          to={`/courses/${entry.course_id}`}
                          className="block min-w-0 rounded-md border border-sky-500/30 bg-sky-500/10 p-1.5 text-[11px] leading-4 text-sky-100 hover:border-sky-400"
                        >
                          <span className="block truncate font-medium">
                            {entry.course_name}
                          </span>
                          {entry.location ? (
                            <span className="block truncate text-sky-200/70">
                              {entry.location}
                            </span>
                          ) : null}
                          <span className="block truncate text-sky-200/60">
                            {entry.weeks_label}
                          </span>
                        </Link>
                      ))}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      ) : null}

      <div className="space-y-3 md:hidden">
        {Array.from({ length: 7 }, (_, index) => index + 1).map((weekday) => {
          const dayEntries = entries
            .filter((entry) => entry.weekday === weekday)
            .sort((a, b) => a.start_time.localeCompare(b.start_time))
          const dayItems = items.filter((item) => item.weekday === weekday)
          if (dayEntries.length === 0 && dayItems.length === 0) return null
          return (
            <section key={weekday} className="card card-pad space-y-2">
              <h3 className="text-sm font-semibold text-ink">
                {WEEKDAY_LABELS[weekday - 1]}
              </h3>
              <ul className="space-y-2">
                {dayEntries.map((entry) => (
                  <li key={entry.id}>
                    <Link
                      to={`/courses/${entry.course_id}`}
                      className="block rounded-lg border border-edge bg-surface-2/60 p-2.5"
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="text-sm font-medium text-ink">
                          {entry.course_name}
                        </span>
                        <span className="shrink-0 text-xs text-muted">
                          {entry.start_time}-{entry.end_time}
                        </span>
                      </div>
                      <p className="text-xs text-muted">
                        {[entry.location, entry.weeks_label].filter(Boolean).join(' · ') ||
                          '地点未设置'}
                      </p>
                    </Link>
                  </li>
                ))}
                {dayItems.map((item) => (
                  <li key={item.id}>
                    <ItemBadge item={item} />
                  </li>
                ))}
              </ul>
            </section>
          )
        })}
      </div>

      {items.length > 0 ? (
        <section className="card card-pad space-y-3">
          <h2 className="text-sm font-semibold text-ink">
            本周任务
            <span className="ml-1.5 text-xs font-normal text-muted">
              （{items.length} 项，含截止提醒）
            </span>
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 7 }, (_, index) => index + 1).map((weekday) => {
              const dayItems = items.filter((item) => item.weekday === weekday)
              if (dayItems.length === 0) return null
              return (
                <div key={weekday} className="min-w-0 space-y-1.5">
                  <p className="text-xs font-medium text-muted">
                    {WEEKDAY_LABELS[weekday - 1]}
                  </p>
                  {dayItems.map((item) => (
                    <ItemBadge key={item.id} item={item} />
                  ))}
                </div>
              )
            })}
          </div>
        </section>
      ) : null}
    </>
  )
}
