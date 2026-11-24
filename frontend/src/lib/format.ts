import type {
  ConnectionKind,
  ConnectionStatus,
  HealthLevel,
  ItemType,
  MatchStatus,
  Priority,
  ProjectStatus,
  Provider,
  SourceType,
  SyncStatus,
  WorkItemStatus,
} from '../api/types'
import { ApiError } from '../api/client'

export const HEALTH_LABELS: Record<HealthLevel, string> = {
  green: '健康',
  yellow: '需关注',
  red: '高风险',
  unknown: '数据不足',
  inactive: '无需评估',
}

export const HEALTH_ICONS: Record<HealthLevel, string> = {
  green: '●',
  yellow: '▲',
  red: '■',
  unknown: '?',
  inactive: '–',
}

export const HEALTH_CLASSES: Record<HealthLevel, string> = {
  green: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  yellow: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  red: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
  unknown: 'bg-slate-500/10 text-slate-300 ring-slate-500/30',
  inactive: 'bg-slate-500/10 text-slate-400 ring-slate-600/40',
}

export const HEALTH_DESCRIPTIONS: Record<HealthLevel, string> = {
  green: '当前未发现规则覆盖的风险',
  yellow: '存在需要关注的健康原因',
  red: '存在阻塞性风险，需要处理',
  unknown: '数据不足，无法判断健康状态',
  inactive: '当前生命周期状态无需健康评估',
}

export const WORK_ITEM_STATUS_LABELS: Record<WorkItemStatus, string> = {
  inbox: '收件箱',
  planned: '已计划',
  in_progress: '进行中',
  done: '已完成',
  dismissed: '已忽略',
}

export const WORK_ITEM_STATUS_CLASSES: Record<WorkItemStatus, string> = {
  inbox: 'bg-slate-500/10 text-slate-300 ring-slate-500/30',
  planned: 'bg-sky-500/10 text-sky-300 ring-sky-500/30',
  in_progress: 'bg-indigo-500/10 text-indigo-300 ring-indigo-500/30',
  done: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  dismissed: 'bg-slate-600/10 text-slate-400 ring-slate-600/40',
}

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  idea: '想法',
  planning: '规划中',
  in_progress: '进行中',
  blocked: '受阻',
  waiting: '等待',
  on_hold: '暂停',
  completed: '已完成',
  cancelled: '已取消',
  archived: '已归档',
}

export const PROJECT_STATUS_CLASSES: Record<ProjectStatus, string> = {
  idea: 'bg-slate-500/10 text-slate-300 ring-slate-500/30',
  planning: 'bg-sky-500/10 text-sky-300 ring-sky-500/30',
  in_progress: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  blocked: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
  waiting: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  on_hold: 'bg-amber-500/10 text-amber-200 ring-amber-500/30',
  completed: 'bg-teal-500/10 text-teal-300 ring-teal-500/30',
  cancelled: 'bg-slate-600/10 text-slate-400 ring-slate-600/40',
  archived: 'bg-slate-600/10 text-slate-400 ring-slate-600/40',
}

export const PROJECT_STATUS_OPTIONS: ProjectStatus[] = [
  'idea',
  'planning',
  'in_progress',
  'blocked',
  'waiting',
  'on_hold',
  'completed',
  'cancelled',
  'archived',
]

export const REASON_REQUIRED_STATUSES: ReadonlySet<ProjectStatus> = new Set<ProjectStatus>([
  'blocked',
  'waiting',
  'on_hold',
  'cancelled',
])

export const RESUME_DATE_STATUSES: ReadonlySet<ProjectStatus> = new Set<ProjectStatus>([
  'waiting',
  'on_hold',
])

export function requiresStatusReason(status: ProjectStatus): boolean {
  return REASON_REQUIRED_STATUSES.has(status)
}

export const PRIORITY_LABELS: Record<Priority, string> = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急',
}

export const PRIORITY_CLASSES: Record<Priority, string> = {
  low: 'bg-slate-500/10 text-slate-300 ring-slate-500/30',
  normal: 'bg-sky-500/10 text-sky-300 ring-sky-500/30',
  high: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  urgent: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
}

export const PRIORITY_ORDER: Priority[] = ['low', 'normal', 'high', 'urgent']

export const SOURCE_LABELS: Record<SourceType, string> = {
  manual: '手动',
  learning: '学习平台',
  academic: '教务',
  github: 'GitHub',
  project: '项目',
}

export const ITEM_TYPE_LABELS: Record<ItemType, string> = {
  task: '任务',
  assignment: '作业',
  exam: '考试',
  milestone: '里程碑',
}

export const CONNECTION_KIND_LABELS: Record<ConnectionKind, string> = {
  academic: '教务平台',
  learning: '学习平台',
}

export const CONNECTION_STATUS_LABELS: Record<ConnectionStatus, string> = {
  unconfigured: '未配置',
  needs_auth: '需要登录',
  ready: '就绪',
  syncing: '同步中',
  error: '出错',
}

export const CONNECTION_STATUS_CLASSES: Record<ConnectionStatus, string> = {
  unconfigured: 'bg-slate-500/10 text-slate-300 ring-slate-500/30',
  needs_auth: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  ready: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  syncing: 'bg-sky-500/10 text-sky-300 ring-sky-500/30',
  error: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
}

export const SYNC_STATUS_LABELS: Record<SyncStatus, string> = {
  running: '同步中',
  succeeded: '成功',
  partial: '部分成功',
  failed: '失败',
  needs_auth: '需要登录',
  interrupted: '已中断',
}

export const SYNC_STATUS_CLASSES: Record<SyncStatus, string> = {
  running: 'bg-sky-500/10 text-sky-300 ring-sky-500/30',
  succeeded: 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30',
  partial: 'bg-amber-500/10 text-amber-300 ring-amber-500/30',
  failed: 'bg-rose-500/10 text-rose-300 ring-rose-500/30',
  needs_auth: 'bg-amber-500/10 text-amber-200 ring-amber-500/30',
  interrupted: 'bg-slate-600/10 text-slate-400 ring-slate-600/40',
}

export const MATCH_STATUS_LABELS: Record<MatchStatus, string> = {
  auto_exact: '自动关联',
  manual: '手动关联',
  unmatched: '待确认',
  ignored: '已忽略',
}

export const PROVIDER_LABELS: Record<Provider, string> = {
  academic_fake: '教务示例源',
  learning_fake: '学习平台示例源',
  academic_portal_v1: '教务门户 v1',
  chaoxing_v1: '学习通 v1',
}

export const PROVIDERS_BY_KIND: Record<ConnectionKind, Provider[]> = {
  academic: ['academic_fake', 'academic_portal_v1'],
  learning: ['learning_fake', 'chaoxing_v1'],
}

export const WORK_ITEM_STATUS_OPTIONS: WorkItemStatus[] = [
  'inbox',
  'planned',
  'in_progress',
  'done',
  'dismissed',
]

export const SOURCE_OPTIONS: SourceType[] = [
  'manual',
  'learning',
  'academic',
  'github',
  'project',
]

export const ERROR_CODE_MESSAGES: Record<string, string> = {
  VALIDATION_ERROR: '提交内容未通过校验，请检查必填项与格式。',
  NOT_FOUND: '资源不存在或已被删除。',
  PROJECT_STATUS_REASON_REQUIRED: '受阻、等待、暂停或取消状态必须填写原因。',
  WORK_ITEM_INVALID_TRANSITION: '该状态流转不被允许（已忽略的事项无法重新激活）。',
  PLATFORM_NOT_CONFIGURED: '该平台适配器尚未实现或未配置，请改用示例源。',
  PLATFORM_AUTH_REQUIRED: '平台登录已失效，请重新登录。',
  PLATFORM_LOGIN_FAILED: '平台登录失败，请检查账号、密码或验证码。',
  PLATFORM_DEPENDENCY_MISSING: '缺少浏览器依赖（Playwright/Chromium），请在后端目录运行 uv sync 与 browser install。',
  PLATFORM_NETWORK_ERROR: '访问平台失败，请检查网络或代理设置。',
  PLATFORM_SYNC_FAILED: '同步失败，请查看同步记录中的错误信息。',
  PLATFORM_STRUCTURE_CHANGED: '平台页面结构可能已变化，部分信息未能读取。',
  SYNC_ALREADY_RUNNING: '该连接已有同步任务在运行，已附着到现有任务。',
  REPO_PATH_INVALID: '仓库路径不存在或不是有效的 Git 仓库。',
  FORBIDDEN_ORIGIN: '请求来源不被允许，请通过本地地址访问。',
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const friendly = ERROR_CODE_MESSAGES[error.code]
    return friendly ? `${friendly}（${error.code}）` : `${error.message}（${error.code}）`
  }
  if (error instanceof Error) return error.message
  return '请求失败，请稍后重试。'
}

export function errorCode(error: unknown): string | null {
  return error instanceof ApiError ? error.code : null
}

export function syncCountsText(counts: {
  courses: number
  items: number
  schedule: number
  adjustments?: number
}): string {
  const parts: string[] = []
  parts.push(`课程 ${counts.courses}`)
  parts.push(`事项 ${counts.items}`)
  if (counts.schedule > 0) parts.push(`课程表 ${counts.schedule}`)
  if ((counts.adjustments ?? 0) > 0) parts.push(`调停补课 ${counts.adjustments}`)
  return parts.join(' · ')
}
