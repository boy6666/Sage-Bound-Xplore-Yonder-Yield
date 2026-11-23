import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useBootstrap } from './api/queries'
import { AppShell } from './components/AppShell'
import { ErrorState } from './components/ErrorState'
import { CourseDetail } from './pages/CourseDetail'
import { Courses } from './pages/Courses'
import { Inbox } from './pages/Inbox'
import { NotFound } from './pages/NotFound'
import { ProjectDetail } from './pages/ProjectDetail'
import { Projects } from './pages/Projects'
import { Schedule } from './pages/Schedule'
import { Settings } from './pages/Settings'
import { Setup } from './pages/Setup'
import { SyncCenter } from './pages/SyncCenter'
import { Today } from './pages/Today'

function BootstrapGate() {
  const bootstrap = useBootstrap()

  if (bootstrap.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="card card-pad max-w-md space-y-2 text-center">
          <p className="text-sm font-semibold text-ink">Student Workbench</p>
          <p className="text-xs text-muted" role="status">
            正在检查本地引导状态…
          </p>
        </div>
      </div>
    )
  }

  if (bootstrap.isError) {
    return (
      <div className="mx-auto max-w-xl px-4 py-10">
        <ErrorState
          error={bootstrap.error}
          title="无法连接本地工作台后端"
          onRetry={() => void bootstrap.refetch()}
        />
        <p className="mt-3 text-xs text-muted">
          请确认本地服务已启动（默认 http://127.0.0.1:8765），并且 Vite 代理配置正确。
        </p>
      </div>
    )
  }

  if (!bootstrap.data.setup_completed) {
    return (
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/setup" element={<Navigate to="/today" replace />} />
      <Route path="/" element={<Navigate to="/today" replace />} />
      <Route element={<AppShell />}>
        <Route path="/today" element={<Today />} />
        <Route path="/inbox" element={<Inbox />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/courses" element={<Courses />} />
        <Route path="/courses/:id" element={<CourseDetail />} />
        <Route path="/schedule" element={<Schedule />} />
        <Route path="/sync" element={<SyncCenter />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <BootstrapGate />
    </BrowserRouter>
  )
}
