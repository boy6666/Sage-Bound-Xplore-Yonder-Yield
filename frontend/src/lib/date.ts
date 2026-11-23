const pad = (value: number): string => String(value).padStart(2, '0')

export function isoWithOffset(date: Date): string {
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMinutes)
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}` +
    `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  )
}

export function todayInTimeZone(timeZone?: string): string {
  const now = new Date()
  try {
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
    const parts = formatter.formatToParts(now)
    const get = (type: string): string =>
      parts.find((part) => part.type === type)?.value ?? ''
    const year = get('year')
    const month = get('month')
    const day = get('day')
    if (year && month && day) return `${year}-${month}-${day}`
  } catch {
    // 无效时区回退到浏览器本地日期。
  }
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

export function localDateOf(value: string, timeZone?: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value.slice(0, 10)
  try {
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
    const parts = formatter.formatToParts(date)
    const get = (type: string): string =>
      parts.find((part) => part.type === type)?.value ?? ''
    const year = get('year')
    const month = get('month')
    const day = get('day')
    if (year && month && day) return `${year}-${month}-${day}`
  } catch {
    // 回退到浏览器本地日期。
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function dayDiff(target: string, base: string): number {
  const targetDate = Date.parse(`${target}T00:00:00Z`)
  const baseDate = Date.parse(`${base}T00:00:00Z`)
  if (Number.isNaN(targetDate) || Number.isNaN(baseDate)) return 0
  return Math.round((targetDate - baseDate) / 86_400_000)
}

export function relativeDay(
  value: string,
  timeZone?: string,
  base: string = todayInTimeZone(timeZone),
): string {
  const diff = dayDiff(localDateOf(value, timeZone), base)
  if (diff === 0) return '今天'
  if (diff === 1) return '明天'
  if (diff === 2) return '后天'
  if (diff === -1) return '昨天'
  if (diff > 0) return `${diff} 天后`
  return `${Math.abs(diff)} 天前`
}

export function formatTime(value: string, timeZone?: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date)
  } catch {
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`
  }
}

export function formatDate(value: string | null | undefined, timeZone?: string): string {
  if (!value) return '未设置'
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value)
  if (Number.isNaN(date.getTime())) return value
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone,
      month: 'long',
      day: 'numeric',
    }).format(date)
  } catch {
    return value
  }
}

export function formatDateTime(
  value: string | null | undefined,
  timeZone?: string,
): string {
  if (!value) return '未设置'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const day = formatDate(value, timeZone)
  const time = formatTime(value, timeZone)
  return `${day} ${time}（${relativeDay(value, timeZone)}）`
}

export function formatDateLong(value: string | null | undefined, timeZone?: string): string {
  if (!value) return '未设置'
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value)
  if (Number.isNaN(date.getTime())) return value
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone,
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(date)
  } catch {
    return value
  }
}

export function formatRelativeSync(value: string | null | undefined): string {
  if (!value) return '从未同步'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const minutes = Math.round((Date.now() - date.getTime()) / 60_000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${Math.round(hours / 24)} 天前`
}

export function localInputToISO(value: string): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return isoWithOffset(date)
}

export function isoToLocalInput(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
}

export function planTodayISO(): string {
  const date = new Date()
  date.setHours(9, 0, 0, 0)
  return isoWithOffset(date)
}

export const WEEKDAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] as const

export function weekdayLabel(weekday: number): string {
  return WEEKDAY_LABELS[weekday - 1] ?? `周${weekday}`
}

export function todayWeekday(): number {
  const day = new Date().getDay()
  return day === 0 ? 7 : day
}

export const TIMEZONE_OPTIONS: string[] = (() => {
  try {
    const supported = (Intl as unknown as { supportedValuesOf?: (key: string) => string[] })
      .supportedValuesOf
    if (typeof supported === 'function') {
      return supported('timeZone')
    }
  } catch {
    // 忽略，使用兜底列表。
  }
  return [
    'Asia/Shanghai',
    'Asia/Hong_Kong',
    'Asia/Tokyo',
    'Asia/Singapore',
    'Europe/London',
    'Europe/Berlin',
    'America/New_York',
    'America/Los_Angeles',
    'UTC',
  ]
})()
