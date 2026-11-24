import { describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Today } from './Today'
import type { TodayDashboard, WorkItem } from '../api/types'
import { requestBody, renderPage, stubFetch } from '../test/utils'

function workItem(overrides: Partial<WorkItem>): WorkItem {
  return {
    id: 'wi-1',
    title: '操作系统实验二',
    notes: null,
    item_type: 'assignment',
    source_type: 'learning',
    status: 'inbox',
    priority: 'high',
    due_at: '2026-11-22T23:59:00+08:00',
    planned_start_at: null,
    planned_end_at: null,
    estimate_minutes: 90,
    blocked_reason: null,
    course_id: 'c1',
    course_name: '操作系统',
    project_id: null,
    project_name: null,
    source_url: 'https://learning.example.com/hw/1',
    external_id: 'hw-1',
    external_status: '未提交',
    needs_review: false,
    created_at: '2026-11-20T09:00:00+08:00',
    updated_at: '2026-11-20T09:00:00+08:00',
    ...overrides,
  }
}

const overdue = workItem({ id: 'wi-1', title: '操作系统实验二', status: 'inbox' })
const upcoming = workItem({
  id: 'wi-2',
  title: '线性代数作业',
  status: 'planned',
  priority: 'normal',
  due_at: '2026-11-25T23:59:00+08:00',
  course_id: 'c2',
  course_name: '线性代数',
  source_type: 'manual',
  source_url: null,
})

const dashboard: TodayDashboard = {
  date: '2026-11-23',
  timezone: 'Asia/Shanghai',
  classes_today: [
    {
      course_id: 'c1',
      course_name: '操作系统',
      start_time: '08:00',
      end_time: '09:40',
      location: '教三-201',
      open_todos: 2,
    },
  ],
  overdue: [overdue],
  today_planned: [],
  upcoming_unplanned: [upcoming],
  blocked: [],
  project_risks: [
    {
      project_id: 'p1',
      name: '个人工作台',
      level: 'red',
      reason: '项目受阻：等助教回复',
    },
  ],
  data_warnings: ['学习通（示例）最近一次同步失败'],
}

function stubToday(data: TodayDashboard = dashboard): ReturnType<typeof stubFetch> {
  return stubFetch([
    (url, _init, method) => {
      if (method === 'GET' && url.endsWith('/api/v1/bootstrap')) {
        return {
          body: {
            setup_completed: true,
            timezone: 'Asia/Shanghai',
            today: '2026-11-23',
            counts: { inbox: 1, today: 0, projects: 1, courses: 2 },
          },
        }
      }
      if (method === 'GET' && url.includes('/api/v1/dashboard/today')) {
        return { body: data }
      }
      if (method === 'PATCH' && url.includes('/api/v1/work-items/')) {
        return { body: workItem({}) }
      }
      return null
    },
  ])
}

describe('Today 今日页', () => {
  it('展示今日课程、分组事项、项目风险与数据提示', async () => {
    stubToday()
    renderPage(<Today />, { route: '/today' })

    expect(
      await screen.findByText('学习通（示例）最近一次同步失败'),
    ).toBeInTheDocument()
    expect(screen.getByText('教三-201')).toBeInTheDocument()
    expect(screen.getByText('操作系统实验二')).toBeInTheDocument()
    expect(screen.getByText('线性代数作业')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /逾期/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /即将截止未安排/ })).toBeInTheDocument()
    expect(screen.getByText('项目受阻：等助教回复')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '个人工作台' })).toHaveAttribute(
      'href',
      '/projects/p1',
    )
  })

  it('标记完成后发送 PATCH {status: "done"}', async () => {
    const fetchMock = stubToday()
    const user = userEvent.setup()
    renderPage(<Today />, { route: '/today' })

    await user.click(
      await screen.findByRole('button', { name: '完成「操作系统实验二」' }),
    )

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).includes('/work-items/wi-1') &&
          (init as RequestInit | undefined)?.method === 'PATCH',
      )
      expect(call).toBeTruthy()
      expect(requestBody(call?.[1] as RequestInit)).toEqual({ status: 'done' })
    })
  })

  it('计划今天会写入 planned_start_at 并把状态设为 planned', async () => {
    const fetchMock = stubToday()
    const user = userEvent.setup()
    renderPage(<Today />, { route: '/today' })

    await user.click(
      await screen.findByRole('button', { name: '计划今天「线性代数作业」' }),
    )

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).includes('/work-items/wi-2') &&
          (init as RequestInit | undefined)?.method === 'PATCH',
      )
      expect(call).toBeTruthy()
      const body = requestBody(call?.[1] as RequestInit) as {
        status?: string
        planned_start_at?: string | null
      }
      expect(body.status).toBe('planned')
      expect(typeof body.planned_start_at).toBe('string')
      expect(body.planned_start_at).toContain('T09:00:00')
    })
  })

  it('显示停课与补课状态', async () => {
    const adjusted: TodayDashboard = {
      ...dashboard,
      classes_today: [
        {
          course_id: 'c1',
          course_name: '操作系统',
          start_time: '08:00',
          end_time: '09:40',
          location: '主5#418',
          open_todos: 0,
          status: 'cancelled',
          adjustment_note: '1-2',
        },
        {
          course_id: 'c1',
          course_name: '操作系统',
          start_time: '10:00',
          end_time: '11:40',
          location: '主5#418',
          open_todos: 0,
          status: 'makeup',
          adjustment_note: '补课 3-4',
        },
      ],
    }
    stubToday(adjusted)
    renderPage(<Today />, { route: '/today' })

    expect(await screen.findByText('已停课')).toBeInTheDocument()
    expect(screen.getByText('补课')).toBeInTheDocument()
  })
})
