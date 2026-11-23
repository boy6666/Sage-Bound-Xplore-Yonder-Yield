import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HealthBadge } from './HealthBadge'
import type { HealthLevel } from '../api/types'
import { HEALTH_LABELS } from '../lib/format'

const LEVELS: HealthLevel[] = ['green', 'yellow', 'red', 'unknown', 'inactive']

describe('HealthBadge', () => {
  it.each(LEVELS)('等级 %s 同时显示文字与可访问名称', (level) => {
    render(<HealthBadge level={level} />)
    expect(
      screen.getByRole('status', { name: `健康状态：${HEALTH_LABELS[level]}` }),
    ).toBeInTheDocument()
    expect(screen.getByText(HEALTH_LABELS[level])).toBeInTheDocument()
  })

  it('unknown 显示“数据不足”，不显示为健康', () => {
    render(<HealthBadge level="unknown" />)
    expect(screen.getByText('数据不足')).toBeInTheDocument()
    expect(screen.queryByText('健康')).not.toBeInTheDocument()
  })

  it('inactive 显示“无需评估”，与数据不足区分', () => {
    render(<HealthBadge level="inactive" />)
    expect(screen.getByText('无需评估')).toBeInTheDocument()
    expect(screen.queryByText('数据不足')).not.toBeInTheDocument()
  })
})
