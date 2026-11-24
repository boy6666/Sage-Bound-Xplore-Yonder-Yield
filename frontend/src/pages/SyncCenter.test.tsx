import { describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SyncCenter } from './SyncCenter'
import type { Connection } from '../api/types'
import { requestBody, renderPage, stubFetch } from '../test/utils'

const connection: Connection = {
  id: 'c1',
  kind: 'learning',
  provider: 'learning_fake',
  display_name: '学习通（示例）',
  status: 'ready',
  account_label: 'demo',
  last_sync_at: '2026-11-22T20:00:00+08:00',
  last_error: null,
  credential_saved: false,
}

describe('SyncCenter 登录与验证码挑战', () => {
  it('账号密码登录返回 challenge 后可提交验证码完成登录', async () => {
    const fetchMock = stubFetch([
      (url, _init, method) => {
        if (method === 'GET' && url.endsWith('/api/v1/connections')) {
          return { body: { items: [connection] } }
        }
        if (method === 'GET' && url.includes('/api/v1/sync-runs')) {
          return { body: { items: [] } }
        }
        if (method === 'POST' && url.endsWith('/api/v1/connections/c1/login')) {
          return {
            body: {
              status: 'challenge',
              challenge: { id: 'ch-1', prompt: '请输入短信验证码' },
            },
          }
        }
        if (
          method === 'POST' &&
          url.endsWith('/api/v1/connections/c1/login/challenge')
        ) {
          return { body: { status: 'ready' } }
        }
        return null
      },
    ])

    const user = userEvent.setup()
    renderPage(<SyncCenter />, { route: '/sync' })

    await screen.findByText('学习通（示例）')
    await user.click(screen.getByRole('button', { name: '登录' }))

    await screen.findByRole('dialog')
    await user.clear(screen.getByLabelText(/账号/))
    await user.type(screen.getByLabelText(/账号/), 'demo')
    await user.type(screen.getByLabelText(/^密码/), 'secret-pass')
    await user.click(screen.getByRole('button', { name: '提交登录' }))

    expect(await screen.findByText('请输入短信验证码')).toBeInTheDocument()

    const loginCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).endsWith('/api/v1/connections/c1/login') &&
        (init as RequestInit | undefined)?.method === 'POST',
    )
    expect(requestBody(loginCall?.[1] as RequestInit)).toEqual({
      username: 'demo',
      password: 'secret-pass',
      save_password: false,
    })

    await user.type(screen.getByLabelText(/验证码/), '123456')
    await user.click(screen.getByRole('button', { name: '提交验证码' }))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith('/api/v1/connections/c1/login/challenge') &&
          (init as RequestInit | undefined)?.method === 'POST',
      )
      expect(call).toBeTruthy()
      expect(requestBody(call?.[1] as RequestInit)).toEqual({
        challenge_id: 'ch-1',
        code: '123456',
      })
    })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('没有连接时展示空状态与新建入口', async () => {
    stubFetch([
      (url, _init, method) => {
        if (method === 'GET' && url.endsWith('/api/v1/connections')) {
          return { body: { items: [] } }
        }
        if (method === 'GET' && url.includes('/api/v1/sync-runs')) {
          return { body: { items: [] } }
        }
        return null
      },
    ])

    renderPage(<SyncCenter />, { route: '/sync' })
    expect(await screen.findByText('还没有平台连接')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '新建连接' }).length).toBeGreaterThan(0)
  })

  it('Cookie 失效时同步失败会自动打开浏览器登录', async () => {
    const academic: Connection = {
      ...connection,
      id: 'ac1',
      kind: 'academic',
      provider: 'academic_portal_v1',
      display_name: '教务系统',
      account_label: null,
    }

    const fetchMock = stubFetch([
      (url, _init, method) => {
        if (method === 'GET' && url.endsWith('/api/v1/connections')) {
          return { body: { items: [academic] } }
        }
        if (method === 'POST' && url.endsWith('/api/v1/connections/ac1/sync')) {
          return { status: 202, body: { sync_run_id: 'run-1' } }
        }
        if (method === 'GET' && url.endsWith('/api/v1/sync-runs/run-1')) {
          return {
            body: {
              id: 'run-1',
              connection_id: 'ac1',
              connection_name: '教务系统',
              kind: 'academic',
              status: 'failed',
              started_at: '2026-11-24T10:00:00+08:00',
              finished_at: '2026-11-24T10:00:05+08:00',
              counts: { courses: 0, items: 0, schedule: 0 },
              error_code: 'PLATFORM_AUTH_REQUIRED',
              error_message: '教务登录已失效，需要重新登录',
            },
          }
        }
        if (method === 'GET' && url.includes('/api/v1/sync-runs')) {
          return { body: { items: [] } }
        }
        if (
          method === 'POST' &&
          url.endsWith('/api/v1/connections/ac1/browser-login')
        ) {
          return {
            body: {
              status: 'ready',
              counts: { courses: 11, items: 0, schedule: 18, adjustments: 0 },
            },
          }
        }
        return null
      },
    ])

    const user = userEvent.setup()
    renderPage(<SyncCenter />, { route: '/sync' })

    await screen.findByText('教务系统')
    await user.click(screen.getByRole('button', { name: '手动同步' }))

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith('/api/v1/connections/ac1/browser-login') &&
          (init as RequestInit | undefined)?.method === 'POST',
      )
      expect(call).toBeTruthy()
    })

    expect(
      await screen.findByText(/登录成功：课程 11 门、课程表 18 条/),
    ).toBeInTheDocument()
  })
})
