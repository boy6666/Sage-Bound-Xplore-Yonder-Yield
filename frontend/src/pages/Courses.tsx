import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Provider, UnmatchedIdentity } from '../api/types'
import {
  useCourses,
  useCreateCourseFromIdentity,
  useLinkIdentity,
  useUnmatchedIdentities,
} from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { weekdayLabel } from '../lib/date'
import {
  MATCH_STATUS_LABELS,
  PROVIDER_LABELS,
  errorMessage,
} from '../lib/format'

function providerText(provider: string): string {
  return PROVIDER_LABELS[provider as Provider] ?? provider
}

function UnmatchedRow({
  entry,
  courses,
}: {
  entry: UnmatchedIdentity
  courses: { id: string; name: string }[]
}) {
  const linkIdentity = useLinkIdentity()
  const createCourse = useCreateCourseFromIdentity()
  const [courseId, setCourseId] = useState(entry.suggested[0]?.course_id ?? '')
  const [newName, setNewName] = useState(entry.identity.external_name)
  const [error, setError] = useState<string | null>(null)

  const handleLink = (): void => {
    if (!courseId) {
      setError('请选择要关联的统一课程。')
      return
    }
    setError(null)
    linkIdentity.mutate({ id: entry.identity.id, courseId })
  }

  const handleCreate = (): void => {
    if (!newName.trim()) {
      setError('新课程名称不能为空。')
      return
    }
    setError(null)
    createCourse.mutate({ id: entry.identity.id, name: newName.trim() })
  }

  return (
    <li className="space-y-2 rounded-lg border border-edge bg-surface-2/40 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">{entry.identity.external_name}</p>
          <p className="text-xs text-muted">
            {providerText(entry.provider)} · {entry.identity.external_id}
            {entry.identity.teacher ? ` · ${entry.identity.teacher}` : ''}
          </p>
        </div>
        <span className="chip bg-amber-500/10 text-amber-300 ring-amber-500/30">
          {MATCH_STATUS_LABELS[entry.identity.match_status]}
        </span>
      </div>

      {entry.suggested.length > 0 ? (
        <p className="text-xs text-muted">
          候选：{entry.suggested.map((item) => item.name).join('、')}
        </p>
      ) : null}

      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs text-muted" htmlFor={`link-${entry.identity.id}`}>
          关联已有课程
        </label>
        <select
          id={`link-${entry.identity.id}`}
          className="input w-auto min-w-40 py-1 text-xs"
          value={courseId}
          onChange={(event) => setCourseId(event.target.value)}
        >
          <option value="">选择课程</option>
          {courses.map((course) => (
            <option key={course.id} value={course.id}>
              {course.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn-sm"
          disabled={linkIdentity.isPending}
          onClick={handleLink}
        >
          关联
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs text-muted" htmlFor={`create-${entry.identity.id}`}>
          创建新课程
        </label>
        <input
          id={`create-${entry.identity.id}`}
          className="input w-auto min-w-40 py-1 text-xs"
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
        />
        <button
          type="button"
          className="btn btn-sm"
          disabled={createCourse.isPending}
          onClick={handleCreate}
        >
          新建并关联
        </button>
      </div>

      {error ? (
        <p role="alert" className="text-xs text-rose-300">
          {error}
        </p>
      ) : null}
      {linkIdentity.isError ? (
        <p role="alert" className="text-xs text-rose-300">
          {errorMessage(linkIdentity.error)}
        </p>
      ) : null}
      {createCourse.isError ? (
        <p role="alert" className="text-xs text-rose-300">
          {errorMessage(createCourse.error)}
        </p>
      ) : null}
    </li>
  )
}

export function Courses() {
  const coursesQuery = useCourses()
  const unmatchedQuery = useUnmatchedIdentities()

  if (coursesQuery.isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        <div className="h-8 w-40 animate-pulse rounded bg-surface-2" />
        <div className="grid gap-3 md:grid-cols-2">
          <div className="h-40 animate-pulse rounded-card bg-surface" />
          <div className="h-40 animate-pulse rounded-card bg-surface" />
        </div>
        <p className="text-xs text-muted">正在加载课程…</p>
      </div>
    )
  }

  if (coursesQuery.isError) {
    return (
      <ErrorState
        error={coursesQuery.error}
        title="课程列表加载失败"
        onRetry={() => void coursesQuery.refetch()}
      />
    )
  }

  const courses = coursesQuery.data.items

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-ink">课程</h1>
        <p className="text-sm text-muted">
          统一课程聚合教务课程表身份与各学习平台身份；未确认的映射需要手动处理。
        </p>
      </header>

      {courses.length === 0 ? (
        <EmptyState
          title="还没有统一课程"
          description="到同步中心添加教务或学习平台连接并完成同步后，课程会出现在这里。"
          action={
            <Link className="btn btn-primary btn-sm" to="/sync">
              前往同步中心
            </Link>
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {courses.map((course) => (
            <article key={course.id} className="card card-pad flex min-w-0 flex-col gap-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="truncate text-base font-semibold text-ink">
                    <Link className="hover:text-accent" to={`/courses/${course.id}`}>
                      {course.name}
                    </Link>
                  </h2>
                  <p className="text-xs text-muted">
                    {[course.code, course.term, course.teacher].filter(Boolean).join(' · ') ||
                      '未提供课程编号与学期'}
                  </p>
                </div>
                <span className="chip bg-surface-2 text-ink ring-edge">
                  待办 {course.open_todos}
                </span>
              </div>

              <div className="space-y-1">
                <p className="text-xs text-muted">来源身份</p>
                {course.identities.length === 0 ? (
                  <p className="text-xs text-muted">尚未关联外部课程身份。</p>
                ) : (
                  <ul className="space-y-1">
                    {course.identities.map((identity) => (
                      <li key={identity.id} className="text-xs text-ink">
                        <span className="chip bg-surface-2 text-muted ring-edge">
                          {providerText(identity.provider)}
                        </span>
                        <span className="ml-1.5 break-words">{identity.external_name}</span>
                        <span className="ml-1 text-muted">
                          （{MATCH_STATUS_LABELS[identity.match_status]}）
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="text-xs text-muted">
                下次上课：
                {course.next_class ? (
                  <span className="text-ink">
                    {weekdayLabel(course.next_class.weekday)}{' '}
                    {course.next_class.start_time}-{course.next_class.end_time}
                    {course.next_class.location ? ` · ${course.next_class.location}` : ''}
                  </span>
                ) : (
                  '暂无课程表条目'
                )}
              </div>

              <Link className="btn btn-sm w-fit" to={`/courses/${course.id}`}>
                查看课程详情
              </Link>
            </article>
          ))}
        </div>
      )}

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-ink">待确认课程身份</h2>
        {unmatchedQuery.isPending ? (
          <p className="text-xs text-muted">正在加载待确认身份…</p>
        ) : unmatchedQuery.isError ? (
          <ErrorState
            error={unmatchedQuery.error}
            title="待确认身份加载失败"
            onRetry={() => void unmatchedQuery.refetch()}
          />
        ) : unmatchedQuery.data.items.length === 0 ? (
          <p className="text-xs text-muted">当前没有待确认的课程映射。</p>
        ) : (
          <ul className="space-y-2">
            {unmatchedQuery.data.items.map((entry) => (
              <UnmatchedRow
                key={entry.identity.id}
                entry={entry}
                courses={courses.map((course) => ({ id: course.id, name: course.name }))}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
