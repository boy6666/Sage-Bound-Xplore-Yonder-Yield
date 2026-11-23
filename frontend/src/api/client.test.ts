import { describe, expect, it, vi } from 'vitest'
import { ApiError, api } from './client'
import { jsonResponse } from '../test/utils'

describe('api client', () => {
  it('GET 请求走 /api/v1 前缀且不携带写请求头', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse({ status: 'ok' }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.get('/bootstrap')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/bootstrap')
    expect(init.method).toBe('GET')
    expect(init.body).toBeUndefined()
    expect(init.headers).toMatchObject({ Accept: 'application/json' })
    const headers = init.headers as Record<string, string>
    expect(headers['Content-Type']).toBeUndefined()
    expect(headers['X-Student-Workbench-Client']).toBeUndefined()
  })

  it('写请求携带 JSON Content-Type 与客户端标识头', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse({ id: 'wi-1' }, 201),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.post('/work-items', { title: '操作系统实验二' })

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/work-items')
    expect(init.method).toBe('POST')
    expect(init.headers).toMatchObject({
      'Content-Type': 'application/json',
      'X-Student-Workbench-Client': 'web',
      Accept: 'application/json',
    })
    expect(JSON.parse(String(init.body))).toEqual({ title: '操作系统实验二' })
  })

  it('PATCH 与 DELETE 也按写请求处理', async () => {
    const fetchMock = vi
      .fn(async (_input: RequestInfo | URL, _init?: RequestInit) => jsonResponse(null))
      .mockResolvedValueOnce(jsonResponse({ id: 'wi-1' }))
      .mockResolvedValueOnce(jsonResponse(undefined, 204))
    vi.stubGlobal('fetch', fetchMock)

    await api.patch('/work-items/wi-1', { priority: 'high' })
    await api.delete('/work-items/wi-1')

    const patchInit = fetchMock.mock.calls[0][1] as RequestInit
    const deleteInit = fetchMock.mock.calls[1][1] as RequestInit
    expect((patchInit.headers as Record<string, string>)['X-Student-Workbench-Client']).toBe('web')
    expect((deleteInit.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(deleteInit.method).toBe('DELETE')
  })

  it('非 2xx 响应解析错误体并抛出 ApiError（code/status/message）', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse(
          {
            error: {
              code: 'PROJECT_STATUS_REASON_REQUIRED',
              message: '受阻状态必须填写原因',
              details: { field: 'status_reason' },
            },
          },
          422,
        ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const error = await api
      .patch('/projects/p1', { status: 'blocked' })
      .then(() => null)
      .catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      code: 'PROJECT_STATUS_REASON_REQUIRED',
      status: 422,
      message: '受阻状态必须填写原因',
      details: { field: 'status_reason' },
    })
  })

  it('错误体不是合法 JSON 时回退为状态码文案', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('invalid json')
        },
        text: async () => 'internal error',
      })),
    )

    const error = await api.get('/bootstrap').catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ code: 'UNKNOWN_ERROR', status: 500 })
    expect((error as ApiError).message).toContain('500')
  })

  it('204 响应不解析 JSON 并返回 undefined', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse(undefined, 204),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.delete('/work-items/wi-1')).resolves.toBeUndefined()
  })
})
