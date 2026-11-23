import { describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProjectDetail } from './ProjectDetail'
import type { Project, ProjectDetail as ProjectDetailData } from '../api/types'
import { requestBody, renderPage, stubFetch } from '../test/utils'

const baseProject: Project = {
  id: 'p1',
  name: '个人工作台',
  description: '本地优先的学生执行系统',
  status: 'in_progress',
  status_reason: null,
  status_changed_at: '2026-11-20T10:00:00+08:00',
  resume_at: null,
  next_action: '完成今日页聚合',
  next_action_updated_at: '2026-11-21T09:00:00+08:00',
  repo_path: 'E:\\code\\workbench',
  open_todos: 0,
  milestones_total: 0,
  milestones_done: 0,
  health: {
    level: 'green',
    reasons: [],
  },
  created_at: '2026-11-01T09:00:00+08:00',
  updated_at: '2026-11-21T09:00:00+08:00',
}

function detail(overrides: Partial<ProjectDetailData> = {}): ProjectDetailData {
  return {
    project: baseProject,
    milestones: [],
    status_history: [],
    repo_snapshot: null,
    todos: [],
    ...overrides,
  }
}

function stubProject(payload: ProjectDetailData): ReturnType<typeof stubFetch> {
  return stubFetch([
    (url, init, method) => {
      if (method === 'GET' && url.endsWith('/api/v1/projects/p1')) {
        return { body: payload }
      }
      if (method === 'PATCH' && url.endsWith('/api/v1/projects/p1')) {
        const body = requestBody(init) as { status?: Project['status']; status_reason?: string }
        return {
          body: {
            ...baseProject,
            status: body.status ?? baseProject.status,
            status_reason: body.status_reason ?? null,
          },
        }
      }
      return null
    },
  ])
}

describe('ProjectDetail 项目详情', () => {
  it('受阻状态未填原因时禁止提交并提示', async () => {
    const fetchMock = stubProject(detail())
    const user = userEvent.setup()
    renderPage(<ProjectDetail />, { route: '/projects/p1', path: '/projects/:id' })

    await screen.findByRole('heading', { level: 1, name: '个人工作台' })
    await user.selectOptions(screen.getByLabelText(/项目状态/), 'blocked')
    await user.click(screen.getByRole('button', { name: '保存状态' }))

    expect(
      await screen.findByText(/必须填写具体原因/),
    ).toBeInTheDocument()

    const patchCalls = fetchMock.mock.calls.filter(
      ([url, init]) =>
        String(url).endsWith('/api/v1/projects/p1') &&
        (init as RequestInit | undefined)?.method === 'PATCH',
    )
    expect(patchCalls).toHaveLength(0)
  })

  it('填写原因后提交 blocked 状态与 reason', async () => {
    const fetchMock = stubProject(detail())
    const user = userEvent.setup()
    renderPage(<ProjectDetail />, { route: '/projects/p1', path: '/projects/:id' })

    await screen.findByRole('heading', { level: 1, name: '个人工作台' })
    await user.selectOptions(screen.getByLabelText(/项目状态/), 'blocked')
    await user.type(screen.getByLabelText(/状态原因/), '等待助教回复环境问题')
    await user.click(screen.getByRole('button', { name: '保存状态' }))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith('/api/v1/projects/p1') &&
          (init as RequestInit | undefined)?.method === 'PATCH',
      )
      expect(call).toBeTruthy()
      expect(requestBody(call?.[1] as RequestInit)).toEqual({
        status: 'blocked',
        status_reason: '等待助教回复环境问题',
        resume_at: null,
      })
    })

    expect(await screen.findByText(/状态已更新/)).toBeInTheDocument()
  })

  it('仓库快照的 null ahead/behind 显示“未知”而不是 0', async () => {
    stubProject(
      detail({
        repo_snapshot: {
          branch: 'main',
          upstream: null,
          ahead: null,
          behind: null,
          dirty_files: null,
          staged_files: 0,
          untracked_files: 0,
          last_commit_at: null,
          last_commit_subject: null,
          scanned_at: '2026-11-22T10:00:00+08:00',
          state: 'ok',
          error: null,
        },
      }),
    )
    renderPage(<ProjectDetail />, { route: '/projects/p1', path: '/projects/:id' })

    await screen.findByRole('heading', { level: 1, name: '个人工作台' })
    expect(screen.getByText('未知 / 未知')).toBeInTheDocument()
    expect(screen.getByText('未知 个文件')).toBeInTheDocument()
    expect(screen.getByText(/相对于本地已有远端引用/)).toBeInTheDocument()
  })
})
