import type { Connection } from '../api/types'
import { formatRelativeSync } from '../lib/date'
import {
  CONNECTION_KIND_LABELS,
  CONNECTION_STATUS_CLASSES,
  CONNECTION_STATUS_LABELS,
} from '../lib/format'

interface SyncStatusCardProps {
  connection: Connection
  syncing?: boolean
  onLogin?: (connection: Connection) => void
  onSync?: (connection: Connection) => void
  onDelete?: (connection: Connection) => void
}

export function SyncStatusCard({
  connection,
  syncing = false,
  onLogin,
  onSync,
  onDelete,
}: SyncStatusCardProps) {
  return (
    <article className="card card-pad space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <h3 className="truncate text-sm font-semibold text-ink">
            {connection.display_name}
          </h3>
          <p className="text-xs text-muted">
            {CONNECTION_KIND_LABELS[connection.kind]} · {connection.provider}
          </p>
        </div>
        <span className={`chip ${CONNECTION_STATUS_CLASSES[connection.status]}`}>
          {CONNECTION_STATUS_LABELS[connection.status]}
        </span>
      </div>

      <dl className="grid gap-1 text-xs text-muted">
        <div className="flex gap-1">
          <dt>账号：</dt>
          <dd className="text-ink">{connection.account_label ?? '未登录'}</dd>
        </div>
        <div className="flex gap-1">
          <dt>最后同步：</dt>
          <dd className="text-ink">{formatRelativeSync(connection.last_sync_at)}</dd>
        </div>
        <div className="flex gap-1">
          <dt>密码保管：</dt>
          <dd className="text-ink">
            {connection.credential_saved ? '已保存到系统凭据库' : '未保存（仅本次登录）'}
          </dd>
        </div>
      </dl>

      {connection.last_error ? (
        <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          最近错误：{connection.last_error}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {onLogin ? (
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => onLogin(connection)}
          >
            {connection.status === 'needs_auth' ? '重新登录' : '登录'}
          </button>
        ) : null}
        {onSync ? (
          <button
            type="button"
            className="btn btn-sm btn-primary"
            disabled={syncing}
            onClick={() => onSync(connection)}
          >
            {syncing ? '同步中…' : '手动同步'}
          </button>
        ) : null}
        {onDelete ? (
          <button
            type="button"
            className="btn btn-sm btn-danger"
            aria-label={`删除连接「${connection.display_name}」`}
            onClick={() => onDelete(connection)}
          >
            删除
          </button>
        ) : null}
      </div>
    </article>
  )
}
