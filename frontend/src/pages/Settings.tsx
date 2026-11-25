import { useEffect, useState, type FormEvent } from 'react'
import {
  useDeleteGithubToken,
  useSaveGithubToken,
  useSettings,
  useUpdateSettings,
} from '../api/queries'
import { ErrorState } from '../components/ErrorState'
import { Field } from '../components/Field'
import { TIMEZONE_OPTIONS } from '../lib/date'
import { errorMessage } from '../lib/format'

export function Settings() {
  const settingsQuery = useSettings()
  const updateSettings = useUpdateSettings()
  const saveToken = useSaveGithubToken()
  const deleteToken = useDeleteGithubToken()

  const [timezone, setTimezone] = useState('Asia/Shanghai')
  const [upcomingDays, setUpcomingDays] = useState('7')
  const [staleHours, setStaleHours] = useState('72')
  const [inactiveDays, setInactiveDays] = useState('14')
  const [savePassword, setSavePassword] = useState(false)
  const [termStart, setTermStart] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [token, setToken] = useState('')
  const [tokenError, setTokenError] = useState<unknown>(null)
  const [tokenMessage, setTokenMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!settingsQuery.data) return
    const data = settingsQuery.data
    setTimezone(data.timezone)
    setUpcomingDays(String(data.upcoming_days))
    setStaleHours(String(data.stale_snapshot_hours))
    setInactiveDays(String(data.inactive_days))
    setSavePassword(data.save_platform_password)
    setTermStart(data.term_start_date ?? '')
  }, [settingsQuery.data])

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    setSaved(false)
    if (!timezone.trim()) {
      setFormError('时区不能为空。')
      return
    }
    const upcoming = Number(upcomingDays)
    const stale = Number(staleHours)
    const inactive = Number(inactiveDays)
    if (!Number.isInteger(upcoming) || upcoming < 1) {
      setFormError('临近截止天数必须是大于 0 的整数。')
      return
    }
    if (!Number.isInteger(stale) || stale < 1) {
      setFormError('快照过期小时数必须是大于 0 的整数。')
      return
    }
    if (!Number.isInteger(inactive) || inactive < 1) {
      setFormError('无活动天数必须是大于 0 的整数。')
      return
    }
    setFormError(null)
    updateSettings.mutate(
      {
        timezone: timezone.trim(),
        upcoming_days: upcoming,
        stale_snapshot_hours: stale,
        inactive_days: inactive,
        save_platform_password: savePassword,
        term_start_date: termStart === '' ? null : termStart,
      },
      { onSuccess: () => setSaved(true) },
    )
  }

  const handleSaveToken = (): void => {
    setTokenError(null)
    setTokenMessage(null)
    if (!token.trim()) {
      setTokenError(new Error('令牌不能为空。'))
      return
    }
    saveToken.mutate(token.trim(), {
      onSuccess: () => {
        setToken('')
        setTokenMessage('令牌已保存到系统凭据库。')
      },
      onError: (error) => setTokenError(error),
    })
  }

  const handleDeleteToken = (): void => {
    setTokenError(null)
    setTokenMessage(null)
    deleteToken.mutate(undefined, {
      onSuccess: () => setTokenMessage('令牌已清除。'),
      onError: (error) => setTokenError(error),
    })
  }

  if (settingsQuery.isPending) {
    return (
      <div className="space-y-3" aria-busy="true">
        <div className="h-8 w-40 animate-pulse rounded bg-surface-2" />
        <div className="h-72 animate-pulse rounded-card bg-surface" />
        <p className="text-xs text-muted">正在加载设置…</p>
      </div>
    )
  }

  if (settingsQuery.isError) {
    return (
      <ErrorState
        error={settingsQuery.error}
        title="设置加载失败"
        onRetry={() => void settingsQuery.refetch()}
      />
    )
  }

  return (
    <div className="max-w-3xl space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-ink">设置</h1>
        <p className="text-sm text-muted">
          修改后会影响“今天/逾期”的判断与项目健康阈值，请确认后再保存。
        </p>
      </header>

      <form className="card card-pad space-y-4" onSubmit={handleSubmit}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            label="时区"
            htmlFor="settings-timezone"
            required
            hint="IANA 时区，例如 Asia/Shanghai。"
          >
            <input
              id="settings-timezone"
              className="input"
              list="settings-timezone-options"
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
              autoComplete="off"
            />
            <datalist id="settings-timezone-options">
              {TIMEZONE_OPTIONS.map((zone) => (
                <option key={zone} value={zone} />
              ))}
            </datalist>
          </Field>

          <Field
            label="第一教学周周一"
            htmlFor="settings-term-start"
            hint="用于推算课程表的教学周与单双周。"
          >
            <input
              id="settings-term-start"
              className="input"
              type="date"
              value={termStart}
              onChange={(event) => setTermStart(event.target.value)}
            />
          </Field>

          <Field
            label="临近截止天数"
            htmlFor="settings-upcoming-days"
            hint="upcoming_days，用于“即将截止未安排”分组。"
          >
            <input
              id="settings-upcoming-days"
              className="input"
              type="number"
              min={1}
              value={upcomingDays}
              onChange={(event) => setUpcomingDays(event.target.value)}
            />
          </Field>

          <Field
            label="快照过期小时数"
            htmlFor="settings-stale-hours"
            hint="stale_snapshot_hours，超过后项目数据视为过期。"
          >
            <input
              id="settings-stale-hours"
              className="input"
              type="number"
              min={1}
              value={staleHours}
              onChange={(event) => setStaleHours(event.target.value)}
            />
          </Field>

          <Field
            label="无活动天数"
            htmlFor="settings-inactive-days"
            hint="inactive_days，超过后项目健康显示“无需评估”。"
          >
            <input
              id="settings-inactive-days"
              className="input"
              type="number"
              min={1}
              value={inactiveDays}
              onChange={(event) => setInactiveDays(event.target.value)}
            />
          </Field>
        </div>

        <label
          className="flex items-start gap-2 rounded-lg border border-edge bg-surface-2/40 p-3 text-sm text-muted"
          htmlFor="settings-save-password"
        >
          <input
            id="settings-save-password"
            type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-edge bg-bg"
            checked={savePassword}
            onChange={(event) => setSavePassword(event.target.checked)}
          />
          <span>
            允许保存平台密码并自动填充（save_platform_password）
            <span className="mt-1 block text-xs">
              密码写入当前 OS 账户的系统凭据库；共享电脑不建议开启。平台会话与密码分开清除。
            </span>
          </span>
        </label>

        {formError ? (
          <p role="alert" className="text-sm text-rose-300">
            {formError}
          </p>
        ) : null}
        {updateSettings.isError ? (
          <p role="alert" className="text-sm text-rose-300">
            {errorMessage(updateSettings.error)}
          </p>
        ) : null}
        {saved ? (
          <p role="status" className="text-sm text-emerald-300">
            设置已保存。
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <button type="submit" className="btn btn-primary" disabled={updateSettings.isPending}>
            {updateSettings.isPending ? '正在保存…' : '保存设置'}
          </button>
          <p className="text-xs text-muted">
            本页只保存本地偏好；课程、作业与项目数据不写入浏览器存储。
          </p>
        </div>
      </form>

      <section className="card card-pad space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">GitHub 访问令牌</h2>
          <span
            className={`chip ${
              settingsQuery.data.github_token_saved
                ? 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30'
                : 'bg-surface-2 text-muted ring-edge'
            }`}
          >
            {settingsQuery.data.github_token_saved ? '已保存' : '未配置'}
          </span>
        </div>
        <p className="text-xs text-muted">
          用于读取私有仓库的 Issue、PR 和 CI 状态。令牌只写入当前 OS
          账户的系统凭据库，不会回显，也不会进入 SQLite、日志或 Git。
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-[260px] flex-1">
            <Field
              label="令牌"
              htmlFor="settings-github-token"
              hint="只需要 repo 只读权限；不确定时先用公开仓库验证。"
            >
              <input
                id="settings-github-token"
                className="input"
                type="password"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder="ghp_..."
                autoComplete="off"
              />
            </Field>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            disabled={saveToken.isPending || !token.trim()}
            onClick={handleSaveToken}
          >
            {saveToken.isPending ? '正在保存…' : '保存令牌'}
          </button>
          {settingsQuery.data.github_token_saved ? (
            <button
              type="button"
              className="btn btn-ghost"
              disabled={deleteToken.isPending}
              onClick={handleDeleteToken}
            >
              清除
            </button>
          ) : null}
        </div>
        {tokenMessage ? (
          <p role="status" className="text-sm text-emerald-300">
            {tokenMessage}
          </p>
        ) : null}
        {tokenError ? (
          <p role="alert" className="text-sm text-rose-300">
            {errorMessage(tokenError)}
          </p>
        ) : null}
      </section>
    </div>
  )
}
