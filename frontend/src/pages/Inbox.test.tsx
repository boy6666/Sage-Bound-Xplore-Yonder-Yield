import { describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Inbox } from './Inbox'
import type { WorkItem, WorkItemInput } from '../api/types'
import { requestBody, renderPage, stubFetch } from '../test/utils'

function makeItem(input: WorkItemInput): WorkItem {
  return {
    id: 'wi-new',
    title: input.title,
    notes: input.notes ?? null,
    item_type: input.item_type ?? 'task',
    source_type: 'manual',
    status: input.status ?? 'inbox',
    priority: input.priority ?? 'normal',
    due_at: input.due_at ?? null,
    planned_start_at: input.planned_start_at ?? null,
    planned_end_at: input.planned_end_at ?? null,
    estimate_minutes: input.estimate_minutes ?? null,
    blocked_reason: input.blocked_reason ?? null,
    course_id: input.course_id ?? null,
    course_name: null,
    project_id: input.project_id ?? null,
    project_name: null,
    source_url: null,
    external_id: null,
    external_status: null,
    needs_review: false,
    created_at: '2026-11-23T09:00:00+08:00',
    updated_at: '2026-11-23T09:00:00+08:00',
  }
}

describe('Inbox 统一收件箱', () => {
  it('可以新建手动事项并在刷新后显示', async () => {
    let items: WorkItem[] = []
    const fetchMock = stubFetch([
      (url, init, method) => {
        if (method === 'GET' && url.includes('/api/v1/work-items')) {
          return { body: { items } }
        }
        if (method === 'POST' && url.endsWith('/api/v1/work-items')) {
          const input = requestBody(init) as WorkItemInput
          const created = makeItem(input)
          items = [created]
          return { status: 201, body: created }
        }
        if (method === 'GET' && url.includes('/api/v1/courses')) {
          return { body: { items: [] } }
        }
        if (method === 'GET' && url.includes('/api/v1/projects')) {
          return { body: { items: [] } }
        }
        return null
      },
    ])

    const user = userEvent.setup()
    renderPage(<Inbox />, { route: '/inbox' })

    expect(await screen.findByText('没有符合条件的事项')).toBeInTheDocument()

    const newButtons = screen.getAllByRole('button', { name: '新建事项' })
    await user.click(newButtons[0])

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    await user.type(screen.getByLabelText(/标题/), '复习线性代数')
    await user.click(screen.getByRole('button', { name: '保存事项' }))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith('/api/v1/work-items') &&
          (init as RequestInit | undefined)?.method === 'POST',
      )
      expect(call).toBeTruthy()
      expect(requestBody(call?.[1] as RequestInit)).toMatchObject({
        title: '复习线性代数',
        status: 'inbox',
        priority: 'normal',
        item_type: 'task',
        course_id: null,
        project_id: null,
      })
    })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    expect(await screen.findByText('复习线性代数')).toBeInTheDocument()
  })

  it('阻塞状态未填原因时阻止提交', async () => {
    const fetchMock = stubFetch([
      (url, _init, method) => {
        if (method === 'GET' && url.includes('/api/v1/work-items')) {
          return { body: { items: [] } }
        }
        if (method === 'GET' && url.includes('/api/v1/courses')) {
          return { body: { items: [] } }
        }
        if (method === 'GET' && url.includes('/api/v1/projects')) {
          return { body: { items: [] } }
        }
        return null
      },
    ])

    const user = userEvent.setup()
    renderPage(<Inbox />, { route: '/inbox' })
    await screen.findByText('没有符合条件的事项')

    await user.click(screen.getAllByRole('button', { name: '新建事项' })[0])
    await user.type(screen.getByLabelText(/标题/), '需要确认的事项')
    await user.click(screen.getByLabelText('标记为受阻'))
    await user.click(screen.getByRole('button', { name: '保存事项' }))

    expect(await screen.findByText('阻塞状态必须填写受阻原因。')).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith('/api/v1/work-items') &&
          (init as RequestInit | undefined)?.method === 'POST',
      ),
    ).toBe(false)
  })
})
