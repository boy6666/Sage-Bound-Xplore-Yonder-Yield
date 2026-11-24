import { describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CourseDetail } from './CourseDetail'
import type { Course, CourseDetailResponse, WorkItemInput } from '../api/types'
import { requestBody, renderPage, stubFetch } from '../test/utils'

const COURSE: Course = {
  id: 'c1',
  name: '操作系统',
  code: null,
  term: '2026-2027-1',
  teacher: '魏滢',
  identities: [],
  open_todos: 0,
  next_class: null,
}

const DETAIL: CourseDetailResponse = {
  course: COURSE,
  schedule: [],
  todos: [],
}

describe('CourseDetail 课程详情', () => {
  it('可以在课程页直接新建作业，并自动带上课程', async () => {
    const fetchMock = stubFetch([
      (url, _init, method) => {
        if (method === 'GET' && url.endsWith('/api/v1/courses/c1')) {
          return { body: DETAIL }
        }
        if (method === 'GET' && url.includes('/api/v1/courses')) {
          return { body: { items: [COURSE] } }
        }
        if (method === 'GET' && url.includes('/api/v1/projects')) {
          return { body: { items: [] } }
        }
        if (method === 'POST' && url.endsWith('/api/v1/work-items')) {
          return { status: 201, body: { id: 'wi-1' } }
        }
        return null
      },
    ])

    const user = userEvent.setup()
    renderPage(<CourseDetail />, { route: '/courses/c1', path: '/courses/:id' })

    expect(await screen.findByText('该课程没有待办')).toBeInTheDocument()

    const buttons = screen.getAllByRole('button', { name: '新建作业 / 任务' })
    await user.click(buttons[0])

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    await user.type(screen.getByLabelText(/标题/), '实验三实验报告')
    await user.click(screen.getByRole('button', { name: '创建' }))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith('/api/v1/work-items') &&
          (init as RequestInit | undefined)?.method === 'POST',
      )
      expect(call).toBeTruthy()
      expect(requestBody(call?.[1] as RequestInit)).toMatchObject({
        title: '实验三实验报告',
        course_id: 'c1',
        item_type: 'assignment',
      })
    })
  })
})
