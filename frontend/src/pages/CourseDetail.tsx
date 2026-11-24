import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { Provider, WorkItemInput } from '../api/types'
import {
  useCourse,
  useCourses,
  useCreateWorkItem,
  useProjects,
  useUnlinkIdentity,
} from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { Modal } from '../components/Modal'
import { WorkItemForm } from '../components/WorkItemForm'
import { WorkItemRow } from '../components/WorkItemRow'
import { weekdayLabel } from '../lib/date'
import { MATCH_STATUS_LABELS, PROVIDER_LABELS, errorMessage } from '../lib/format'

function providerText(provider: string): string {
  return PROVIDER_LABELS[provider as Provider] ?? provider
}

export function CourseDetail() {
  const { id } = useParams<{ id: string }>()
  const courseQuery = useCourse(id)
  const unlinkIdentity = useUnlinkIdentity()
  const coursesQuery = useCourses()
  const projectsQuery = useProjects()
  const createItem = useCreateWorkItem()
  const [formOpen, setFormOpen] = useState(false)

  const closeForm = (): void => {
    setFormOpen(false)
    createItem.reset()
  }

  const handleCreate = (input: WorkItemInput): void => {
    createItem.mutate(input, { onSuccess: () => closeForm() })
  }

  const handleUnlink = (identityId: string, name: string): void => {
    const confirmed = window.confirm(
      `确定解除「${name}」与本课程的关联吗？该操作只调整映射，不会删除来源作业。`,
    )
    if (confirmed) unlinkIdentity.mutate(identityId)
  }

  if (!id) {
    return <ErrorState error={new Error('缺少课程 ID')} title="无法打开课程" />
  }

  if (courseQuery.isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        <div className="h-8 w-48 animate-pulse rounded bg-surface-2" />
        <div className="h-40 animate-pulse rounded-card bg-surface" />
        <p className="text-xs text-muted">正在加载课程详情…</p>
      </div>
    )
  }

  if (courseQuery.isError) {
    return (
      <div className="space-y-3">
        <ErrorState
          error={courseQuery.error}
          title="课程详情加载失败"
          onRetry={() => void courseQuery.refetch()}
        />
        <Link className="btn btn-sm" to="/courses">
          返回课程列表
        </Link>
      </div>
    )
  }

  const { course, schedule, todos } = courseQuery.data

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <Link className="text-xs text-muted hover:text-accent" to="/courses">
          ← 返回课程列表
        </Link>
        <h1 className="break-words text-xl font-semibold text-ink">{course.name}</h1>
        <p className="text-sm text-muted">
          {[course.code, course.term, course.teacher].filter(Boolean).join(' · ') ||
            '未提供课程编号与学期'}
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card card-pad space-y-3">
          <h2 className="text-sm font-semibold text-ink">平台身份</h2>
          {course.identities.length === 0 ? (
            <p className="text-xs text-muted">
              尚未关联外部课程身份。可在课程页的“待确认课程身份”中关联。
            </p>
          ) : (
            <ul className="space-y-2">
              {course.identities.map((identity) => (
                <li key={identity.id} className="rounded-lg border border-edge bg-surface-2/40 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="break-words text-sm font-medium text-ink">
                        {identity.external_name}
                      </p>
                      <p className="text-xs text-muted">
                        {providerText(identity.provider)} · 外部 ID：{identity.external_id}
                        {identity.teacher ? ` · ${identity.teacher}` : ''}
                      </p>
                    </div>
                    <span className="chip bg-surface-2 text-muted ring-edge">
                      {MATCH_STATUS_LABELS[identity.match_status]}
                    </span>
                  </div>
                  {identity.match_status !== 'unmatched' ? (
                    <button
                      type="button"
                      className="btn btn-sm btn-ghost mt-2"
                      disabled={unlinkIdentity.isPending}
                      aria-label={`解除「${identity.external_name}」与本课程的关联`}
                      onClick={() =>
                        handleUnlink(identity.id, identity.external_name)
                      }
                    >
                      解除关联
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {unlinkIdentity.isError ? (
            <p role="alert" className="text-xs text-rose-300">
              {errorMessage(unlinkIdentity.error)}
            </p>
          ) : null}
        </section>

        <section className="card card-pad space-y-3">
          <h2 className="text-sm font-semibold text-ink">课程表条目</h2>
          {schedule.length === 0 ? (
            <p className="text-xs text-muted">该课程暂无课程表条目。</p>
          ) : (
            <ul className="space-y-2">
              {schedule.map((entry) => (
                <li
                  key={entry.id}
                  className="rounded-lg border border-edge bg-surface-2/40 px-3 py-2 text-sm"
                >
                  <p className="text-ink">
                    {weekdayLabel(entry.weekday)} {entry.start_time}-{entry.end_time}
                  </p>
                  <p className="text-xs text-muted">
                    {[entry.location ?? '地点未设置', entry.weeks_label].filter(Boolean).join(' · ')}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">
            跨平台待办
            <span className="ml-1.5 text-xs font-normal text-muted">
              （未完成 {course.open_todos} 项）
            </span>
          </h2>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={() => setFormOpen(true)}
          >
            新建作业 / 任务
          </button>
        </div>
        {todos.length === 0 ? (
          <EmptyState
            title="该课程没有待办"
            description="学习平台同步的作业与手动创建的事项会同时出现在这里，互不覆盖。"
            action={
              <button
                type="button"
                className="btn btn-sm btn-primary"
                onClick={() => setFormOpen(true)}
              >
                新建作业 / 任务
              </button>
            }
          />
        ) : (
          <div className="space-y-2">
            {todos.map((item) => (
              <WorkItemRow key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>

      <Modal
        open={formOpen}
        title="新建作业 / 任务"
        description={`已归属课程「${course.name}」。填写计划开始时间后，该事项会出现在日程表里。`}
        onClose={closeForm}
        widthClass="max-w-2xl"
      >
        <WorkItemForm
          key={`course-${course.id}`}
          initial={{ course_id: course.id, item_type: 'assignment' }}
          courses={coursesQuery.data?.items ?? []}
          projects={projectsQuery.data?.items ?? []}
          submitting={createItem.isPending}
          serverError={createItem.error}
          onSubmit={handleCreate}
          onCancel={closeForm}
          submitLabel="创建"
        />
      </Modal>
    </div>
  )
}
