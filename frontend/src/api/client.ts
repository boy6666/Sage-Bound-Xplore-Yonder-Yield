const BASE_URL = '/api/v1'
const CLIENT_HEADER = 'X-Student-Workbench-Client'

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown>

  constructor(
    code: string,
    message: string,
    status: number,
    details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

interface RequestOptions {
  method?: HttpMethod
  body?: unknown
  signal?: AbortSignal
}

const WRITE_METHODS: ReadonlySet<HttpMethod> = new Set<HttpMethod>([
  'POST',
  'PATCH',
  'PUT',
  'DELETE',
])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json' }

  if (WRITE_METHODS.has(method)) {
    headers['Content-Type'] = 'application/json'
    headers[CLIENT_HEADER] = 'web'
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
    credentials: 'same-origin',
  })

  if (!response.ok) {
    let code = 'UNKNOWN_ERROR'
    let message = `请求失败（HTTP ${response.status}）`
    let details: Record<string, unknown> = {}

    try {
      const payload: unknown = await response.json()
      if (isRecord(payload) && isRecord(payload.error)) {
        const error = payload.error
        if (typeof error.code === 'string' && error.code.length > 0) {
          code = error.code
        }
        if (typeof error.message === 'string' && error.message.length > 0) {
          message = error.message
        }
        if (isRecord(error.details)) {
          details = error.details
        }
      }
    } catch {
      // 非 JSON 错误体：保留基于状态码的兜底文案。
    }

    throw new ApiError(code, message, response.status, details)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  if (text.trim() === '') {
    return undefined as T
  }

  return JSON.parse(text) as T
}

export type QueryValue = string | number | boolean | null | undefined

export function queryString(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.set(key, String(value))
  }
  const text = search.toString()
  return text === '' ? '' : `?${text}`
}

export const api = {
  get<T>(path: string, signal?: AbortSignal): Promise<T> {
    return request<T>(path, { signal })
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'POST', body: body ?? {} })
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'PATCH', body: body ?? {} })
  },
  delete<T = void>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' })
  },
}
