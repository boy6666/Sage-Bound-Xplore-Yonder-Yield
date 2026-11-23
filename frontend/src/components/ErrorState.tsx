import { errorCode, errorMessage } from '../lib/format'

interface ErrorStateProps {
  error: unknown
  title?: string
  onRetry?: () => void
}

export function ErrorState({ error, title = '加载失败', onRetry }: ErrorStateProps) {
  const code = errorCode(error)
  return (
    <div
      role="alert"
      className="card card-pad space-y-3 border-rose-500/40 bg-rose-950/20"
    >
      <div className="space-y-1">
        <p className="text-base font-semibold text-rose-200">{title}</p>
        <p className="text-sm text-rose-100/80">{errorMessage(error)}</p>
        {code ? <p className="text-xs text-rose-200/60">错误代码：{code}</p> : null}
      </div>
      {onRetry ? (
        <button type="button" className="btn btn-sm" onClick={onRetry}>
          重试
        </button>
      ) : null}
    </div>
  )
}
