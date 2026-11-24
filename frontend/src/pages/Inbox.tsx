import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { WorkItem, WorkItemInput, WorkItemStatus } from '../api/types'
import {
  useCourses,
  useCreateWorkItem,
  useDeleteWorkItem,
  useProjects,
  useUpdateWorkItem,
  useWorkItems,
} from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { Field } from '../components/Field'
import { Modal } from '../components/Modal'
import { WorkItemForm } from '../components/WorkItemForm'
import { WorkItemRow } from '../components/WorkItemRow'
import { planTodayISO } from '../lib/date'
import {
  SOURCE_LABELS,
  SOURCE_OPTIONS,
  WORK_ITEM_STATUS_LABELS,
  WORK_ITEM_STATUS_OPTIONS,
} from '../lib/format'

export function Inbox() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = (searchParams.get('status') ?? '') as WorkItemStatus | ''
  const sourceType = (searchParams.get('source_type') ?? '') as WorkItem['source_type'] | ''
  const courseId = searchParams.get('course_id') ?? ''
  const projectId = searchParams.get('project_id') ?? ''
  const q = searchParams.get('q') ?? ''

  const itemsQuery = useWorkItems({
    status,
    source_type: sourceType,
    course_id: courseId,
    project_id: projectId,
    q,
    limit: 100,
  })
  const coursesQuery = useCourses()
  const projectsQuery = useProjects()
  const createItem = useCreateWorkItem()
  const updateItem = useUpdateWorkItem()
  const deleteItem = useDeleteWorkItem()

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<WorkItem | null>(null)

  const setFilter = (key: string, value: string): void => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearchParams(next, { replace: true })
  }

  const openCreate = (): void => {
    setEditing(null)
    setFormOpen(true)
  }

  const openEdit = (item: WorkItem): void => {
    setEditing(item)
    setFormOpen(true)
  }

  const closeForm = (): void => {
    setFormOpen(false)
    setEditing(null)
    createItem.reset()
    updateItem.reset()
  }

  const handleSubmit = (input: WorkItemInput): void => {
    if (editing) {
      updateItem.mutate(
        { id: editing.id, patch: input },
        { onSuccess: () => closeForm() },
      )
    } else {
      createItem.mutate(input, { onSuccess: () => closeForm() })
    }
  }

  const handleDelete = (item: WorkItem): void => {
    if (window.confirm(`确定删除「${item.title}」吗？该操作不可撤销。`)) {
      deleteItem.mutate(item.id)
    }
  }

  const items = (itemsQuery.data?.items ?? []).filter((item) => {
    if (status) return true
    return item.status !== 'done' && item.status !== 'dismissed'
  })

  const actionError = createItem.error ?? updateItem.error ?? deleteItem.error

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">统一收件箱</h1>
          <p className="text-sm text-muted">
            汇总学习平台、项目与手动事项；筛选条件会保留在地址栏。
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          新建事项
        </button>
      </header>

      <section className="card card-pad space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="来源" htmlFor="filter-source">
            <select
              id="filter-source"
              className="input"
              value={sourceType}
              onChange={(event) => setFilter('source_type', event.target.value)}
            >
              <option value="">全部来源</option>
              {SOURCE_OPTIONS.map((source) => (
                <option key={source} value={source}>
                  {SOURCE_LABELS[source]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="课程" htmlFor="filter-course">
            <select
              id="filter-course"
              className="input"
              value={courseId}
              onChange={(event) => setFilter('course_id', event.target.value)}
            >
              <option value="">全部课程</option>
              {(coursesQuery.data?.items ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {course.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="项目" htmlFor="filter-project">
            <select
              id="filter-project"
              className="input"
              value={projectId}
              onChange={(event) => setFilter('project_id', event.target.value)}
            >
              <option value="">全部项目</option>
              {(projectsQuery.data?.items ?? []).map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="状态" htmlFor="filter-status">
            <select
              id="filter-status"
              className="input"
              value={status}
              onChange={(event) => setFilter('status', event.target.value)}
            >
              <option value="">未处理</option>
              {WORK_ITEM_STATUS_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {WORK_ITEM_STATUS_LABELS[value]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="搜索" htmlFor="filter-q">
            <input
              id="filter-q"
              className="input"
              value={q}
              placeholder="按标题模糊搜索"
              onChange={(event) => setFilter('q', event.target.value)}
            />
          </Field>
        </div>
      </section>

      {actionError ? <ErrorState error={actionError} title="事项操作失败" /> : null}

      {itemsQuery.isPending ? (
        <div className="space-y-2" aria-busy="true">
          <div className="h-20 animate-pulse rounded-card bg-surface" />
          <div className="h-20 animate-pulse rounded-card bg-surface" />
          <p className="text-xs text-muted">正在加载事项…</p>
        </div>
      ) : itemsQuery.isError ? (
        <ErrorState
          error={itemsQuery.error}
          title="收件箱加载失败"
          onRetry={() => void itemsQuery.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="没有符合条件的事项"
          description="调整筛选条件，或新建一个手动事项。学习平台事项会在同步后出现在这里。"
          action={
            <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
              新建事项
            </button>
          }
        />
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted">共 {items.length} 项</p>
          {items.map((item) => (
            <WorkItemRow
              key={item.id}
              item={item}
              busy={updateItem.isPending || deleteItem.isPending}
              onComplete={(target) =>
                updateItem.mutate({ id: target.id, patch: { status: 'done' } })
              }
              onPlanToday={(target) =>
                updateItem.mutate({
                  id: target.id,
                  patch: { status: 'planned', planned_start_at: planTodayISO() },
                })
              }
              onPriorityChange={(target, priority) =>
                updateItem.mutate({ id: target.id, patch: { priority } })
              }
              onEdit={openEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <Modal
        open={formOpen}
        title={editing ? '编辑事项' : '新建事项'}
        description="截止时间与计划执行时间是两个独立字段。来源平台字段不可在本地改写。"
        onClose={closeForm}
        widthClass="max-w-2xl"
      >
        <WorkItemForm
          key={editing?.id ?? 'new'}
          initial={editing}
          courses={coursesQuery.data?.items ?? []}
          projects={projectsQuery.data?.items ?? []}
          submitting={createItem.isPending || updateItem.isPending}
          serverError={createItem.error ?? updateItem.error}
          onSubmit={handleSubmit}
          onCancel={closeForm}
        />
      </Modal>
    </div>
  )
}
