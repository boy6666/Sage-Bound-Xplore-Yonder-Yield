import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiError } from '../api/client'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'

describe('EmptyState', () => {
  it('展示标题、描述与动作', () => {
    render(
      <EmptyState
        title="还没有项目"
        description="创建第一个项目"
        action={<button type="button">新建项目</button>}
      />,
    )
    expect(screen.getByText('还没有项目')).toBeInTheDocument()
    expect(screen.getByText('创建第一个项目')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '新建项目' })).toBeInTheDocument()
  })
})

describe('ErrorState', () => {
  it('展示错误码、友好文案并支持重试', async () => {
    const onRetry = vi.fn()
    const error = new ApiError(
      'PROJECT_STATUS_REASON_REQUIRED',
      '受阻状态必须填写原因',
      422,
    )
    render(<ErrorState error={error} onRetry={onRetry} />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/必须填写原因/)).toBeInTheDocument()
    expect(screen.getAllByText(/PROJECT_STATUS_REASON_REQUIRED/).length).toBeGreaterThan(0)

    await userEvent.click(screen.getByRole('button', { name: '重试' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('非 ApiError 也有兜底文案', () => {
    render(<ErrorState error={new Error('网络不可达')} />)
    expect(screen.getByText('网络不可达')).toBeInTheDocument()
  })
})
