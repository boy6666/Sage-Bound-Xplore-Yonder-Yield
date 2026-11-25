import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { ProjectStatus } from '../api/types'
import { useCreateProject, useProjects } from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { Field } from '../components/Field'
import { Modal } from '../components/Modal'
import { ProjectCard } from '../components/ProjectCard'
import {
  PROJECT_STATUS_LABELS,
  PROJECT_STATUS_OPTIONS,
  errorMessage,
} from '../lib/format'

export function Projects() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = (searchParams.get('status') ?? '') as ProjectStatus | ''
  const projectsQuery = useProjects(status || undefined)
  const createProject = useCreateProject()
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [newStatus, setNewStatus] = useState<ProjectStatus>('planning')
  const [repoPath, setRepoPath] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const resetForm = (): void => {
    setName('')
    setDescription('')
    setNewStatus('planning')
    setRepoPath('')
    setFormError(null)
    createProject.reset()
  }

  const closeModal = (): void => {
    setOpen(false)
    resetForm()
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!name.trim()) {
      setFormError('项目名称不能为空。')
      return
    }
    setFormError(null)
    createProject.mutate(
      {
        name: name.trim(),
        description: description.trim() === '' ? null : description.trim(),
        status: newStatus,
        repo_path: repoPath.trim() === '' ? null : repoPath.trim(),
      },
      {
        onSuccess: (project) => {
          closeModal()
          navigate(`/projects/${project.id}`)
        },
      },
    )
  }

  const setFilter = (value: string): void => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set('status', value)
    else next.delete('status')
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">项目</h1>
          <p className="text-sm text-muted">
            生命周期状态与健康等级分开呈现；健康原因由后端规则计算。
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
          新建项目
        </button>
      </header>

      <section className="card card-pad flex flex-wrap items-end gap-3">
        <Field label="按状态筛选" htmlFor="project-status-filter" className="w-48 space-y-1">
          <select
            id="project-status-filter"
            className="input"
            value={status}
            onChange={(event) => setFilter(event.target.value)}
          >
            <option value="">全部状态</option>
            {PROJECT_STATUS_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {PROJECT_STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </Field>
        <p className="text-xs text-muted">
          {projectsQuery.data ? `共 ${projectsQuery.data.items.length} 个项目` : ''}
        </p>
      </section>

      {projectsQuery.isPending ? (
        <div className="grid gap-3 md:grid-cols-2" aria-busy="true">
          <div className="h-56 animate-pulse rounded-card bg-surface" />
          <div className="h-56 animate-pulse rounded-card bg-surface" />
        </div>
      ) : projectsQuery.isError ? (
        <ErrorState
          error={projectsQuery.error}
          title="项目列表加载失败"
          onRetry={() => void projectsQuery.refetch()}
        />
      ) : projectsQuery.data.items.length === 0 ? (
        <EmptyState
          title="还没有项目"
          description="创建第一个项目，关联本地仓库后可查看健康原因与里程碑进度。"
          action={
            <button type="button" className="btn btn-primary btn-sm" onClick={() => setOpen(true)}>
              新建项目
            </button>
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {projectsQuery.data.items.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      <Modal open={open} title="新建项目" onClose={closeModal} widthClass="max-w-xl">
        <form className="space-y-3" onSubmit={handleSubmit}>
          <Field label="项目名称" htmlFor="project-name" required>
            <input
              id="project-name"
              className="input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：个人工作台"
            />
          </Field>
          <Field label="项目说明" htmlFor="project-description">
            <textarea
              id="project-description"
              className="input min-h-20"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="初始状态" htmlFor="project-status">
              <select
                id="project-status"
                className="input"
                value={newStatus}
                onChange={(event) => setNewStatus(event.target.value as ProjectStatus)}
              >
                {PROJECT_STATUS_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {PROJECT_STATUS_LABELS[value]}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label="本地仓库路径"
              htmlFor="project-repo"
              hint="可稍后在详情页补充；没有 Git 的目录也可以。"
            >
              <input
                id="project-repo"
                className="input"
                value={repoPath}
                onChange={(event) => setRepoPath(event.target.value)}
                placeholder="E:\code\project"
              />
            </Field>
          </div>

          {formError ? (
            <p role="alert" className="text-sm text-rose-300">
              {formError}
            </p>
          ) : null}
          {createProject.isError ? (
            <p role="alert" className="text-sm text-rose-300">
              {errorMessage(createProject.error)}
            </p>
          ) : null}

          <div className="flex flex-wrap justify-end gap-2 pt-1">
            <button type="button" className="btn btn-ghost" onClick={closeModal}>
              取消
            </button>
            <button type="submit" className="btn btn-primary" disabled={createProject.isPending}>
              {createProject.isPending ? '正在创建…' : '创建项目'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
