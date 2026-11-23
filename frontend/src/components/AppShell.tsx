import { NavLink, Outlet, useLocation } from 'react-router-dom'

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: '/today', label: '今日' },
  { to: '/inbox', label: '收件箱' },
  { to: '/projects', label: '项目' },
  { to: '/courses', label: '课程' },
  { to: '/schedule', label: '课程表' },
  { to: '/sync', label: '同步中心' },
  { to: '/settings', label: '设置' },
]

const TITLES: { prefix: string; title: string }[] = [
  { prefix: '/today', title: '今日' },
  { prefix: '/inbox', title: '统一收件箱' },
  { prefix: '/projects', title: '项目' },
  { prefix: '/courses', title: '课程' },
  { prefix: '/schedule', title: '课程表' },
  { prefix: '/sync', title: '同步中心' },
  { prefix: '/settings', title: '设置' },
  { prefix: '/setup', title: '首次引导' },
]

function titleFor(pathname: string): string {
  const match = TITLES.find(
    (entry) => pathname === entry.prefix || pathname.startsWith(`${entry.prefix}/`),
  )
  return match?.title ?? 'Student Workbench'
}

export function AppShell() {
  const location = useLocation()
  const title = titleFor(location.pathname)

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col md:flex-row">
      <aside className="border-b border-edge bg-surface/60 md:min-h-screen md:w-56 md:shrink-0 md:border-b-0 md:border-r">
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 md:flex-col md:items-start md:gap-1 md:px-5 md:py-6">
          <div>
            <p className="text-sm font-semibold tracking-wide text-ink">
              Student Workbench
            </p>
            <p className="text-[11px] text-muted">本地优先的学生执行系统</p>
          </div>
          <NavLink
            to="/sync"
            className="text-xs text-muted hover:text-accent md:hidden"
          >
            同步中心
          </NavLink>
        </div>
        <nav
          aria-label="主导航"
          className="flex flex-wrap gap-1 px-2 pb-2 md:flex-col md:gap-0.5 md:px-3 md:pb-6"
        >
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-accent/15 font-medium text-accent'
                    : 'text-muted hover:bg-surface-2 hover:text-ink'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-edge bg-bg/70 px-4 py-3 backdrop-blur md:px-8">
          <h1 className="text-lg font-semibold text-ink">{title}</h1>
          <div className="flex items-center gap-3">
            <NavLink
              to="/settings"
              className="hidden text-xs text-muted hover:text-accent sm:inline"
            >
              本地偏好
            </NavLink>
            <NavLink to="/sync" className="btn btn-sm">
              同步状态
            </NavLink>
          </div>
        </header>
        <main className="min-w-0 flex-1 px-4 py-5 md:px-8 md:py-7">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
