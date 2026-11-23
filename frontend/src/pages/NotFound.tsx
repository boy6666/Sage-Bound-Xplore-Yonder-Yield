import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="card card-pad space-y-3">
      <p className="text-xs uppercase tracking-[0.2em] text-muted">404</p>
      <h1 className="text-xl font-semibold text-ink">页面不存在</h1>
      <p className="text-sm text-muted">
        地址可能已失效，或者资源已被删除。返回今日页继续处理事项。
      </p>
      <Link className="btn btn-primary btn-sm w-fit" to="/today">
        返回今日
      </Link>
    </div>
  )
}
