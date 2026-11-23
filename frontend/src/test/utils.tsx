import type { ReactElement, ReactNode } from 'react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: 0 },
    },
  })
}

export function renderWithProviders(ui: ReactElement): ReturnType<typeof render> {
  const client = createTestQueryClient()
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

export function renderPage(
  ui: ReactElement,
  { route = '/', path = '*' }: { route?: string; path?: string } = {},
): ReturnType<typeof render> {
  const client = createTestQueryClient()
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

export function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  } as unknown as Response
}

interface MockResult {
  status?: number
  body?: unknown
}

type Handler = (
  url: string,
  init: RequestInit | undefined,
  method: string,
) => MockResult | null

export function stubFetch(handlers: Handler[]): ReturnType<typeof vi.fn> {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = (init?.method ?? 'GET').toUpperCase()
    for (const handler of handlers) {
      const result = handler(url, init, method)
      if (result) return jsonResponse(result.body, result.status ?? 200)
    }
    return jsonResponse(
      { error: { code: 'NOT_FOUND', message: `未模拟的请求：${method} ${url}` } },
      404,
    )
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

export function requestBody(init: RequestInit | undefined): unknown {
  if (!init || typeof init.body !== 'string') return undefined
  return JSON.parse(init.body) as unknown
}

export function renderInRouter(node: ReactNode): ReturnType<typeof render> {
  return render(<MemoryRouter>{node}</MemoryRouter>)
}
