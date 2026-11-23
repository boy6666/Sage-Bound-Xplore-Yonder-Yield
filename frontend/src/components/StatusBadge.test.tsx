import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('展示事项状态中文名', () => {
    render(<StatusBadge status="in_progress" />)
    expect(screen.getByText('进行中')).toBeInTheDocument()
  })

  it('项目受阻状态同时展示具体原因', () => {
    render(<StatusBadge kind="project" status="blocked" reason="等助教回复环境问题" />)
    expect(screen.getByText('受阻')).toBeInTheDocument()
    expect(screen.getByText('等助教回复环境问题')).toBeInTheDocument()
  })

  it('项目等待状态无原因时只展示状态', () => {
    render(<StatusBadge kind="project" status="waiting" reason={null} />)
    expect(screen.getByText('等待')).toBeInTheDocument()
  })
})
