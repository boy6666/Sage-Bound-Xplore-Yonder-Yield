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
})
