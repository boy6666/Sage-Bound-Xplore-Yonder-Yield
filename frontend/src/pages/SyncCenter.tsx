import { useEffect, useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import type {
  Connection,
  ConnectionKind,
  LoginChallenge,
  Provider,
  SyncRun,
} from '../api/types'
import {
  useConnectionChallenge,
  useConnectionLogin,
  useConnections,
  useCreateConnection,
  useDeleteConnection,
  useSyncConnection,
  useSyncRun,
  useSyncRuns,
} from '../api/queries'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { Field } from '../components/Field'
import { Modal } from '../components/Modal'
import { SyncStatusCard } from '../components/SyncStatusCard'
import { formatDateTime, formatRelativeSync } from '../lib/date'
import {
  CONNECTION_KIND_LABELS,
  ERROR_CODE_MESSAGES,
  PROVIDER_LABELS,
  PROVIDERS_BY_KIND,
  SYNC_STATUS_CLASSES,
  SYNC_STATUS_LABELS,
  errorMessage,
  syncCountsText,
} from '../lib/format'

function LoginPanel({
  connection,
  onSuccess,
  onCancel,
}: {
  connection: Connection
  onSuccess: () => void
  onCancel: () => void
}) {
  const login = useConnectionLogin(connection.id)
  const challengeMutation = useConnectionChallenge(connection.id)
  const [username, setUsername] = useState(connection.account_label ?? '')
  const [password, setPassword] = useState('')
  const [savePassword, setSavePassword] = useState(connection.credential_saved)
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const handleCredentials = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    setError(null)
    setNotice(null)
    if (!username.trim()) {
      setError(new Error('请输入平台账号。'))
      return
    }
    if (!password) {
      setError(new Error('请输入平台密码。'))
      return
    }
    login.mutate(
      { username: username.trim(), password, save_password: savePassword },
      {
        onSuccess: (data) => {
          setPassword('')
          if (data.status === 'challenge' && data.challenge) {
            setChallenge(data.challenge)
            setNotice('平台要求二次验证，请输入验证码完成登录。')
          } else {
            onSuccess()
          }
        },
        onError: (mutationError) => setError(mutationError),
      },
    )
  }

  const handleChallenge = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!challenge) return
    setError(null)
    if (!code.trim()) {
      setError(new Error('请输入验证码。'))
      return
    }
    challengeMutation.mutate(
      { challenge_id: challenge.id, code: code.trim() },
      {
        onSuccess: () => {
          setCode('')
          onSuccess()
        },
        onError: (mutationError) => setError(mutationError),
      },
    )
  }

  if (challenge) {
    return (
      <form className="space-y-3" onSubmit={handleChallenge}>
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
          {challenge.prompt}
        </p>
        <Field label="验证码" htmlFor="login-challenge-code" required>
          <input
            id="login-challenge-code"
            className="input"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            autoComplete="one-time-code"
          />
        </Field>
        {notice ? <p className="text-xs text-muted">{notice}</p> : null}
        {error ? (
          <p role="alert" className="text-sm text-rose-300">
            {errorMessage(error)}
          </p>
        ) : null}
        <div className="flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setChallenge(null)
              setCode('')
              setError(null)
            }}
          >
            返回账号密码
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={challengeMutation.isPending}
          >
            {challengeMutation.isPending ? '正在验证…' : '提交验证码'}
          </button>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>
          取消登录
        </button>
      </form>
    )
  }

  return (
    <form className="space-y-3" onSubmit={handleCredentials}>
      <p className="text-xs text-muted">
        密码只用于本次登录；选择保存后写入系统凭据库，不会进入 SQLite、Git 或浏览器存储。
      </p>
      <Field label="账号" htmlFor="login-username" required>
        <input
          id="login-username"
          className="input"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
        />
      </Field>
      <Field label="密码" htmlFor="login-password" required>
        <input
          id="login-password"
          className="input"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
        />
      </Field>
      <label className="flex items-center gap-2 text-sm text-muted" htmlFor="login-save-password">
        <input
          id="login-save-password"
          type="checkbox"
          className="h-4 w-4 rounded border-edge bg-bg"
          checked={savePassword}
          onChange={(event) => setSavePassword(event.target.checked)}
        />
        保存密码到系统凭据库
      </label>

      {error ? (
        <p role="alert" className="text-sm text-rose-300">
          {errorMessage(error)}
        </p>
      ) : null}

      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          取消
        </button>
        <button type="submit" className="btn btn-primary" disabled={login.isPending}>
          {login.isPending ? '正在登录…' : '提交登录'}
        </button>
      </div>
    </form>
  )
}

function ActiveRunCard({ runId }: { runId: string }) {
  const runQuery = useSyncRun(runId)
  if (runQuery.isPending) {
    return <p className="text-xs text-muted">正在读取同步任务状态…</p>
  }
  if (runQuery.isError) {
    return <ErrorState error={runQuery.error} title="同步任务状态读取失败" />
  }
  const run = runQuery.data
  return (
    <div className="rounded-lg border border-edge bg-surface-2/40 p-3 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-ink">{run.connection_name}</p>
        <span className={`chip ${SYNC_STATUS_CLASSES[run.status]}`}>
          {SYNC_STATUS_LABELS[run.status]}
        </span>
      </div>
      <p className="mt-1 text-muted">
        开始：{formatDateTime(run.started_at)}
        {run.finished_at ? ` · 结束：${formatDateTime(run.finished_at)}` : ''}
      </p>
      <p className="mt-1 text-muted">统计：{syncCountsText(run.counts)}</p>
      {run.error_message ? (
        <p className="mt-1 text-rose-300">
          {run.error_code
            ? `[${run.error_code}] ${
                ERROR_CODE_MESSAGES[run.error_code] ?? run.error_message
              }`
            : run.error_message}
        </p>
      ) : null}
    </div>
  )
}

function SyncRunRow({ run }: { run: SyncRun }) {
  return (
    <li className="rounded-lg border border-edge bg-surface-2/30 px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-ink">{run.connection_name}</p>
        <span className={`chip ${SYNC_STATUS_CLASSES[run.status]}`}>
          {SYNC_STATUS_LABELS[run.status]}
        </span>
      </div>
      <p className="text-xs text-muted">
        {CONNECTION_KIND_LABELS[run.kind]} · 开始 {formatRelativeSync(run.started_at)}
        {run.finished_at ? ` · 结束 ${formatRelativeSync(run.finished_at)}` : ''}
      </p>
      <p className="text-xs text-muted">统计：{syncCountsText(run.counts)}</p>
      {run.error_code || run.error_message ? (
        <p className="mt-1 text-xs text-rose-300">
          {run.error_code
            ? `[${run.error_code}] ${
                ERROR_CODE_MESSAGES[run.error_code] ?? run.error_message ?? '同步失败'
              }`
            : (run.error_message ?? '同步失败')}
        </p>
      ) : null}
    </li>
  )
}

export function SyncCenter() {
  const connectionsQuery = useConnections()
  const syncRunsQuery = useSyncRuns(20)
  const createConnection = useCreateConnection()
  const deleteConnection = useDeleteConnection()
  const syncConnection = useSyncConnection()
  const queryClient = useQueryClient()

  const [loginTarget, setLoginTarget] = useState<Connection | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [syncMessage, setSyncMessage] = useState<string | null>(null)
  const [syncError, setSyncError] = useState<unknown>(null)
  const [historyKind, setHistoryKind] = useState<'' | ConnectionKind>('')

  const [kind, setKind] = useState<ConnectionKind>('learning')
  const [provider, setProvider] = useState<Provider>('learning_fake')
  const [displayName, setDisplayName] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)

  const activeRun = useSyncRun(activeRunId)
  const activeStatus = activeRun.data?.status

  useEffect(() => {
    if (!activeStatus || activeStatus === 'running') return
    void queryClient.invalidateQueries({ queryKey: ['connections'] })
    void queryClient.invalidateQueries({ queryKey: ['sync-runs'] })
    void queryClient.invalidateQueries({ queryKey: ['courses'] })
    void queryClient.invalidateQueries({ queryKey: ['work-items'] })
    void queryClient.invalidateQueries({ queryKey: ['schedule'] })
    void queryClient.invalidateQueries({ queryKey: ['today'] })
  }, [activeStatus, queryClient])

  const handleSync = (connection: Connection): void => {
    setSyncError(null)
    setSyncMessage(null)
    syncConnection.mutate(connection.id, {
      onSuccess: (data) => {
        setActiveRunId(data.sync_run_id)
        setSyncMessage(`已开始同步「${connection.display_name}」，任务结束后会自动刷新数据。`)
      },
      onError: (error) => {
        if (error instanceof ApiError && error.code === 'SYNC_ALREADY_RUNNING') {
          const id = error.details.sync_run_id
          if (typeof id === 'string' && id.length > 0) {
            setActiveRunId(id)
            setSyncMessage('该连接已有同步任务在运行，已附着到现有任务。')
            return
          }
        }
        setSyncError(error)
      },
    })
  }

  const handleDelete = (connection: Connection): void => {
    if (window.confirm(`确定删除连接「${connection.display_name}」吗？`)) {
      deleteConnection.mutate(connection.id)
    }
  }

  const handleCreate = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault()
    if (!displayName.trim()) {
      setCreateError('连接名称不能为空。')
      return
    }
    setCreateError(null)
    createConnection.mutate(
      { kind, provider, display_name: displayName.trim() },
      {
        onSuccess: (connection) => {
          setCreateOpen(false)
          setDisplayName('')
          setLoginTarget(connection)
        },
      },
    )
  }

  const changeKind = (next: ConnectionKind): void => {
    setKind(next)
    setProvider(PROVIDERS_BY_KIND[next][0])
  }

  const runs = (syncRunsQuery.data?.items ?? []).filter((run) =>
    historyKind ? run.kind === historyKind : true,
  )

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">同步中心</h1>
          <p className="text-sm text-muted">
            教务与学习平台分别独立同步；失败时保留旧数据，可重新登录或重试。
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setCreateOpen(true)}>
          新建连接
        </button>
      </header>

      {syncMessage ? (
        <p role="status" className="rounded-lg border border-sky-500/40 bg-sky-500/10 px-3 py-2 text-sm text-sky-100">
          {syncMessage}
        </p>
      ) : null}
      {syncError ? <ErrorState error={syncError} title="同步启动失败" /> : null}
      {syncConnection.isError && !syncError ? (
        <ErrorState error={syncConnection.error} title="同步请求失败" />
      ) : null}
      {deleteConnection.isError ? (
        <ErrorState error={deleteConnection.error} title="删除连接失败" />
      ) : null}

      {activeRunId ? (
        <section className="card card-pad space-y-2">
          <h2 className="text-sm font-semibold text-ink">当前同步任务</h2>
          <ActiveRunCard runId={activeRunId} />
        </section>
      ) : null}

      {connectionsQuery.isPending ? (
        <div className="grid gap-3 md:grid-cols-2" aria-busy="true">
          <div className="h-40 animate-pulse rounded-card bg-surface" />
          <div className="h-40 animate-pulse rounded-card bg-surface" />
        </div>
      ) : connectionsQuery.isError ? (
        <ErrorState
          error={connectionsQuery.error}
          title="连接列表加载失败"
          onRetry={() => void connectionsQuery.refetch()}
        />
      ) : connectionsQuery.data.items.length === 0 ? (
        <EmptyState
          title="还没有平台连接"
          description="添加教务或学习平台连接后可同步课程表、课程身份和作业。示例源适合本地联调。"
          action={
            <button type="button" className="btn btn-primary btn-sm" onClick={() => setCreateOpen(true)}>
              新建连接
            </button>
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {connectionsQuery.data.items.map((connection) => (
            <SyncStatusCard
              key={connection.id}
              connection={connection}
              syncing={
                syncConnection.isPending && syncConnection.variables === connection.id
              }
              onLogin={setLoginTarget}
              onSync={handleSync}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <section className="card card-pad space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-ink">同步历史</h2>
          <label className="flex items-center gap-2 text-xs text-muted" htmlFor="sync-history-kind">
            按来源筛选
            <select
              id="sync-history-kind"
              className="input w-auto py-1 text-xs"
              value={historyKind}
              onChange={(event) => setHistoryKind(event.target.value as '' | ConnectionKind)}
            >
              <option value="">全部</option>
              <option value="academic">教务</option>
              <option value="learning">学习平台</option>
            </select>
          </label>
        </div>

        {syncRunsQuery.isPending ? (
          <p className="text-xs text-muted">正在加载同步历史…</p>
        ) : syncRunsQuery.isError ? (
          <ErrorState
            error={syncRunsQuery.error}
            title="同步历史加载失败"
            onRetry={() => void syncRunsQuery.refetch()}
          />
        ) : runs.length === 0 ? (
          <p className="text-xs text-muted">还没有同步记录。</p>
        ) : (
          <ul className="space-y-2">
            {runs.map((run) => (
              <SyncRunRow key={run.id} run={run} />
            ))}
          </ul>
        )}
      </section>

      <Modal
        open={Boolean(loginTarget)}
        title={loginTarget ? `登录「${loginTarget.display_name}」` : '平台登录'}
        description="账号密码只提交给本地后端；验证码由用户本人完成。"
        onClose={() => setLoginTarget(null)}
      >
        {loginTarget ? (
          <LoginPanel
            key={loginTarget.id}
            connection={loginTarget}
            onSuccess={() => setLoginTarget(null)}
            onCancel={() => setLoginTarget(null)}
          />
        ) : null}
      </Modal>

      <Modal open={createOpen} title="新建平台连接" onClose={() => setCreateOpen(false)}>
        <form className="space-y-3" onSubmit={handleCreate}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="连接类型" htmlFor="connection-kind">
              <select
                id="connection-kind"
                className="input"
                value={kind}
                onChange={(event) => changeKind(event.target.value as ConnectionKind)}
              >
                <option value="academic">教务平台</option>
                <option value="learning">学习平台</option>
              </select>
            </Field>
            <Field label="适配器" htmlFor="connection-provider">
              <select
                id="connection-provider"
                className="input"
                value={provider}
                onChange={(event) => setProvider(event.target.value as Provider)}
              >
                {PROVIDERS_BY_KIND[kind].map((value) => (
                  <option key={value} value={value}>
                    {PROVIDER_LABELS[value]}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="连接名称" htmlFor="connection-name" required>
            <input
              id="connection-name"
              className="input"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="例如：学习通（示例）"
            />
          </Field>

          {createError ? (
            <p role="alert" className="text-sm text-rose-300">
              {createError}
            </p>
          ) : null}
          {createConnection.isError ? (
            <p role="alert" className="text-sm text-rose-300">
              {errorMessage(createConnection.error)}
            </p>
          ) : null}

          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setCreateOpen(false)}
            >
              取消
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createConnection.isPending}
            >
              创建并登录
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
