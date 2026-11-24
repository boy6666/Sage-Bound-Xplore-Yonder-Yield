import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { ScheduleGrid } from './ScheduleGrid'
import type { ScheduleEntry, ScheduleItem } from '../api/types'
import { renderInRouter } from '../test/utils'

const ENTRY: ScheduleEntry = {
  id: 'e1',
  course_id: 'c1',
  course_name: '操作系统',
  weekday: 1,
  start_time: '08:00',
  end_time: '09:40',
  location: '主5#418',
  weeks: [1, 2, 3],
  weeks_label: '1-3周(每周)',
}

function makeItem(overrides: Partial<ScheduleItem> = {}): ScheduleItem {
  return {
    id: 'i1',
    title: '实验二报告',
    weekday: 2,
    kind: 'planned',
    time_label: '14:00',
    item_type: 'assignment',
    priority: 'normal',
    status: 'planned',
    course_id: 'c1',
    course_name: '操作系统',
    due_at: null,
    planned_start_at: '2026-11-24T14:00:00+08:00',
    ...overrides,
  }
}

describe('ScheduleGrid 日程网格', () => {
  it('课程与本周任务同时显示', () => {
    renderInRouter(<ScheduleGrid entries={[ENTRY]} items={[makeItem()]} />)

    expect(screen.getAllByText('操作系统').length).toBeGreaterThan(0)
    expect(screen.getByText('本周任务')).toBeInTheDocument()
    expect(screen.getAllByText('实验二报告').length).toBeGreaterThan(0)
    expect(screen.getAllByText('14:00').length).toBeGreaterThan(0)
  })

  it('只有任务没有课程时也渲染', () => {
    renderInRouter(<ScheduleGrid entries={[]} items={[makeItem()]} />)

    expect(screen.queryByText('本周没有课程')).not.toBeInTheDocument()
    expect(screen.getAllByText('实验二报告').length).toBeGreaterThan(0)
  })

  it('截止提醒使用截止时间标签', () => {
    renderInRouter(
      <ScheduleGrid
        entries={[]}
        items={[makeItem({ id: 'i2', kind: 'due', time_label: '截止 23:59' })]}
      />,
    )

    expect(screen.getAllByText('截止 23:59').length).toBeGreaterThan(0)
  })

  it('课程和任务都为空时显示空状态', () => {
    renderInRouter(<ScheduleGrid entries={[]} items={[]} />)
    expect(screen.getByText('本周没有课程')).toBeInTheDocument()
  })
})
