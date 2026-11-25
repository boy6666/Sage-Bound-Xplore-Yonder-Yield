import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'
import { api, queryString } from './client'
import type {
  Bootstrap,
  Connection,
  ConnectionKind,
  Course,
  CourseDetailResponse,
  CourseIdentity,
  Health,
  LoginResponse,
  Milestone,
  Project,
  ProjectDetail,
  ProjectInput,
  ProjectPatch,
  RepoSnapshot,
  ScheduleResponse,
  Settings,
  SyncRun,
  TodayDashboard,
  UnmatchedIdentity,
  WorkItem,
  WorkItemFilters,
  WorkItemInput,
  WorkItemPatch,
} from './types'

export function normalizeWorkItemFilters(filters: WorkItemFilters): WorkItemFilters {
  const normalized: WorkItemFilters = {}
  if (filters.status) normalized.status = filters.status
  if (filters.source_type) normalized.source_type = filters.source_type
  if (filters.project_id) normalized.project_id = filters.project_id
  if (filters.course_id) normalized.course_id = filters.course_id
  if (filters.q) normalized.q = filters.q
  if (typeof filters.limit === 'number') normalized.limit = filters.limit
  return normalized
}

export const workItemKeys = {
  all: ['work-items'] as const,
  list: (filters: WorkItemFilters) =>
    ['work-items', normalizeWorkItemFilters(filters)] as const,
}

export const projectKeys = {
  all: ['projects'] as const,
  list: (status?: string) => ['projects', status ?? 'all'] as const,
  detail: (id: string) => ['project', id] as const,
}

export const courseKeys = {
  all: ['courses'] as const,
  detail: (id: string) => ['course', id] as const,
}

export const scheduleKeys = {
  all: ['schedule'] as const,
  week: (week?: number) => ['schedule', week ?? 'current'] as const,
}

export const todayKeys = {
  all: ['today'] as const,
  date: (date: string) => ['today', date] as const,
}

export const connectionKeys = {
  all: ['connections'] as const,
}

export const syncRunKeys = {
  all: ['sync-runs'] as const,
  list: (limit: number) => ['sync-runs', 'list', limit] as const,
  detail: (id: string) => ['sync-runs', 'detail', id] as const,
}

export const settingsKeys = {
  all: ['settings'] as const,
}

export const bootstrapKeys = {
  all: ['bootstrap'] as const,
}

export const identityKeys = {
  unmatched: ['course-identities', 'unmatched'] as const,
}

function invalidateWorkItemRelated(client: QueryClient): void {
  void client.invalidateQueries({ queryKey: ['today'] })
  void client.invalidateQueries({ queryKey: ['work-items'] })
  void client.invalidateQueries({ queryKey: ['projects'] })
  void client.invalidateQueries({ queryKey: ['project'] })
  void client.invalidateQueries({ queryKey: ['courses'] })
  void client.invalidateQueries({ queryKey: ['course'] })
  void client.invalidateQueries({ queryKey: ['schedule'] })
}

function invalidateProjectRelated(client: QueryClient): void {
  void client.invalidateQueries({ queryKey: ['projects'] })
  void client.invalidateQueries({ queryKey: ['project'] })
  void client.invalidateQueries({ queryKey: ['today'] })
}

export function useBootstrap() {
  return useQuery({
    queryKey: bootstrapKeys.all,
    queryFn: () => api.get<Bootstrap>('/bootstrap'),
    staleTime: 15_000,
    retry: 1,
  })
}

export function useCompleteBootstrap() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: { timezone: string; term_start_date: string }) =>
      api.post<Bootstrap>('/bootstrap/complete', input),
    onSuccess: (data) => {
      client.setQueryData(bootstrapKeys.all, data)
      void client.invalidateQueries({ queryKey: bootstrapKeys.all })
      void client.invalidateQueries({ queryKey: ['today'] })
      void client.invalidateQueries({ queryKey: ['connections'] })
      void client.invalidateQueries({ queryKey: ['projects'] })
      void client.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}

export function useToday(date: string) {
  return useQuery({
    queryKey: todayKeys.date(date),
    queryFn: () => api.get<TodayDashboard>(`/dashboard/today${queryString({ date })}`),
    enabled: date.length > 0,
  })
}

export function useWorkItems(filters: WorkItemFilters) {
  return useQuery({
    queryKey: workItemKeys.list(filters),
    queryFn: () => api.get<{ items: WorkItem[] }>(`/work-items${queryString({ ...filters })}`),
  })
}

export function useWorkItem(id: string | undefined) {
  return useQuery({
    queryKey: ['work-items', 'detail', id ?? ''],
    queryFn: () => api.get<WorkItem>(`/work-items/${id}`),
    enabled: Boolean(id),
  })
}

export function useCreateWorkItem() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: WorkItemInput) => api.post<WorkItem>('/work-items', input),
    onSuccess: () => invalidateWorkItemRelated(client),
  })
}

export function useUpdateWorkItem() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: WorkItemPatch }) =>
      api.patch<WorkItem>(`/work-items/${id}`, patch),
    onSuccess: () => invalidateWorkItemRelated(client),
  })
}

export function useDeleteWorkItem() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/work-items/${id}`),
    onSuccess: () => invalidateWorkItemRelated(client),
  })
}

export function useProjects(status?: string) {
  return useQuery({
    queryKey: projectKeys.list(status),
    queryFn: () => api.get<{ items: Project[] }>(`/projects${queryString({ status })}`),
  })
}

export function useProject(id: string | undefined) {
  return useQuery({
    queryKey: projectKeys.detail(id ?? ''),
    queryFn: () => api.get<ProjectDetail>(`/projects/${id}`),
    enabled: Boolean(id),
  })
}

export function useCreateProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: ProjectInput) => api.post<Project>('/projects', input),
    onSuccess: () => invalidateProjectRelated(client),
  })
}

export function useDeleteProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/projects/${id}`),
    onSuccess: () => {
      invalidateProjectRelated(client)
      void client.invalidateQueries({ queryKey: ['work-items'] })
    },
  })
}

export function useUpdateProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: ProjectPatch }) =>
      api.patch<Project>(`/projects/${id}`, patch),
    onSuccess: () => {
      invalidateProjectRelated(client)
      void client.invalidateQueries({ queryKey: ['today'] })
    },
  })
}

export function useAddMilestone() {  const client = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      title,
      due_at,
    }: {
      projectId: string
      title: string
      due_at: string | null
    }) => api.post<Milestone>(`/projects/${projectId}/milestones`, { title, due_at }),
    onSuccess: () => invalidateProjectRelated(client),
  })
}

export function useUpdateMilestone() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: string
      projectId: string
      patch: { title?: string; due_at?: string | null; status?: 'open' | 'done' }
    }) => api.patch<Milestone>(`/milestones/${id}`, patch),
    onSuccess: () => invalidateProjectRelated(client),
  })
}

export function useAddProjectTodo() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, input }: { projectId: string; input: WorkItemInput }) =>
      api.post<WorkItem>(`/projects/${projectId}/todos`, input),
    onSuccess: () => invalidateWorkItemRelated(client),
  })
}

export function useScanProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) =>
      api.post<{ snapshot: RepoSnapshot | null; health: Health }>(
        `/projects/${projectId}/scan`,
      ),
    onSuccess: () => {
      invalidateProjectRelated(client)
      void client.invalidateQueries({ queryKey: ['sync-runs'] })
    },
  })
}

export function useCourses() {
  return useQuery({
    queryKey: courseKeys.all,
    queryFn: () => api.get<{ items: Course[] }>('/courses'),
  })
}

export function useCreateCourse() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      name: string
      code?: string | null
      term?: string | null
      teacher?: string | null
    }) => api.post<Course>('/courses', input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['courses'] })
      void client.invalidateQueries({ queryKey: ['schedule'] })
    },
  })
}

export function useCourse(id: string | undefined) {
  return useQuery({
    queryKey: courseKeys.detail(id ?? ''),
    queryFn: () => api.get<CourseDetailResponse>(`/courses/${id}`),
    enabled: Boolean(id),
  })
}

export function useSchedule(week?: number) {
  return useQuery({
    queryKey: scheduleKeys.week(week),
    queryFn: () => api.get<ScheduleResponse>(`/courses/schedule${queryString({ week })}`),
  })
}

export function useUnmatchedIdentities() {
  return useQuery({
    queryKey: identityKeys.unmatched,
    queryFn: () => api.get<{ items: UnmatchedIdentity[] }>('/course-identities/unmatched'),
  })
}

export function useLinkIdentity() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, courseId }: { id: string; courseId: string }) =>
      api.post<CourseIdentity>(`/course-identities/${id}/link`, { course_id: courseId }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['courses'] })
      void client.invalidateQueries({ queryKey: ['course'] })
      void client.invalidateQueries({ queryKey: ['course-identities'] })
      void client.invalidateQueries({ queryKey: ['schedule'] })
      void client.invalidateQueries({ queryKey: ['work-items'] })
      void client.invalidateQueries({ queryKey: ['today'] })
    },
  })
}

export function useUnlinkIdentity() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post<CourseIdentity>(`/course-identities/${id}/unlink`),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['courses'] })
      void client.invalidateQueries({ queryKey: ['course'] })
      void client.invalidateQueries({ queryKey: ['course-identities'] })
      void client.invalidateQueries({ queryKey: ['schedule'] })
      void client.invalidateQueries({ queryKey: ['work-items'] })
      void client.invalidateQueries({ queryKey: ['today'] })
    },
  })
}

export function useCreateCourseFromIdentity() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      api.post<Course>(`/course-identities/${id}/create-course`, { name }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['courses'] })
      void client.invalidateQueries({ queryKey: ['course-identities'] })
      void client.invalidateQueries({ queryKey: ['schedule'] })
    },
  })
}

export function useConnections() {
  return useQuery({
    queryKey: connectionKeys.all,
    queryFn: () => api.get<{ items: Connection[] }>('/connections'),
  })
}

export function useCreateConnection() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      kind: ConnectionKind
      provider: string
      display_name: string
    }) => api.post<Connection>('/connections', input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['connections'] })
    },
  })
}

export function useDeleteConnection() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/connections/${id}`),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['connections'] })
      void client.invalidateQueries({ queryKey: ['sync-runs'] })
    },
  })
}

export function useConnectionLogin(connectionId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: { username: string; password: string; save_password: boolean }) =>
      api.post<LoginResponse>(`/connections/${connectionId}/login`, input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['connections'] })
    },
  })
}

export function useConnectionChallenge(connectionId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: { challenge_id: string; code: string }) =>
      api.post<LoginResponse>(`/connections/${connectionId}/login/challenge`, input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['connections'] })
    },
  })
}

export function useSyncConnection() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (connectionId: string) =>
      api.post<{ sync_run_id: string }>(`/connections/${connectionId}/sync`),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['connections'] })
      void client.invalidateQueries({ queryKey: ['sync-runs'] })
    },
  })
}

export function useBrowserLogin() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (connectionId: string) =>
      api.post<{ status: string; counts: Record<string, number> }>(
        `/connections/${connectionId}/browser-login`,
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['connections'] })
      void client.invalidateQueries({ queryKey: ['sync-runs'] })
      void client.invalidateQueries({ queryKey: ['courses'] })
      void client.invalidateQueries({ queryKey: ['course'] })
      void client.invalidateQueries({ queryKey: ['schedule'] })
      void client.invalidateQueries({ queryKey: ['today'] })
    },
  })
}

export function useSyncRun(id: string | null) {
  return useQuery({
    queryKey: syncRunKeys.detail(id ?? ''),
    queryFn: () => api.get<SyncRun>(`/sync-runs/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.status === 'running' ? 1000 : false
    },
  })
}

export function useSyncRuns(limit = 20) {
  return useQuery({
    queryKey: syncRunKeys.list(limit),
    queryFn: () => api.get<{ items: SyncRun[] }>(`/sync-runs${queryString({ limit })}`),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? []
      return items.some((run) => run.status === 'running') ? 2000 : false
    },
  })
}

export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.all,
    queryFn: () => api.get<Settings>('/settings'),
  })
}

export function useUpdateSettings() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (patch: Partial<Settings>) => api.patch<Settings>('/settings', patch),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: settingsKeys.all })
      void client.invalidateQueries({ queryKey: ['today'] })
      void client.invalidateQueries({ queryKey: ['projects'] })
      void client.invalidateQueries({ queryKey: ['schedule'] })
    },
  })
}

export function useSaveGithubToken() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (token: string) =>
      api.put<{ saved: boolean }>('/settings/github-token', { token }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}

export function useDeleteGithubToken() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api.delete('/settings/github-token'),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}
