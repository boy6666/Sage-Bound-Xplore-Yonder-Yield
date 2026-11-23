import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProjectCard } from './ProjectCard'
import type { Project } from '../api/types'

const project: Project = {
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
  open_todos: 3,
  milestones_total: 2,
  milestones_done: 1,
  health: {
    level: 'yellow',
    reasons: [
      {
        code: 'REPO_DIRTY',
        label: '工作区有未提交修改',
        detail: '2 个文件',
        action: 'repo',
      },
    ],
  },
  created_at: '2026-11-01T09:00:00+08:00',
  updated_at: '2026-11-21T09:00:00+08:00',
}

function renderCard(): void {
  render(
    <MemoryRouter>
      <ProjectCard project={project} />
    </MemoryRouter>,
  )
}

describe('ProjectCard', () => {
  it('展示状态、健康、待办数与里程碑进度', () => {
    renderCard()
    expect(screen.getByRole('link', { name: '个人工作台' })).toHaveAttribute(
      'href',
      '/projects/p1',
    )
    expect(screen.getByText('进行中')).toBeInTheDocument()
    expect(screen.getByRole('status', { name: '健康状态：需关注' })).toBeInTheDocument()
    expect(screen.getByText('3 项未完成')).toBeInTheDocument()
    expect(screen.getByText('1/2 个完成')).toBeInTheDocument()
    expect(screen.getByText('里程碑进度 50%')).toBeInTheDocument()
    expect(
      screen.getByRole('progressbar', { name: '个人工作台 里程碑进度' }),
    ).toHaveAttribute('aria-valuenow', '50')
  })

  it('健康原因可展开查看并包含证据', () => {
    renderCard()
    expect(screen.getByText('健康原因（1）')).toBeInTheDocument()
    expect(screen.getByText('工作区有未提交修改')).toBeInTheDocument()
    expect(screen.getByText(/2 个文件/)).toBeInTheDocument()
    expect(screen.getByText('完成今日页聚合')).toBeInTheDocument()
  })
})
