# Student Workbench — 前端规范

- 文档版本：0.3.0
- 技术基线：React 19、TypeScript 5.9、Vite 8、React Router 7、TanStack Query 5、Ant Design 6
- 页面流程见 `APP_FLOW.md`，接口契约见 `BACKEND_STRUCTURE.md`

## 1. 前端目标与边界

前端负责：

- 页面展示、路由、表单和本地交互反馈。
- 通过同源 REST API 查询和修改本地工作台数据。
- 用 TanStack Query 管理服务端状态与同步轮询。
- 清楚区分加载、空、错误、过期、同步中和待核实状态。

前端不负责：

- 直接访问教务/学习平台或 GitHub API。
- 读取学校 Cookie、GitHub token 或本地文件系统。
- 执行 Git 命令。
- 在浏览器中实现项目健康规则的另一份副本。
- 使用 localStorage 保存课程、作业、令牌或业务数据库。

后端是业务规则与数据的唯一事实来源。

## 2. 目录结构

```text
apps/web/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── providers.tsx
│   │   ├── router.tsx
│   │   ├── query-client.ts
│   │   └── route-error.tsx
│   ├── api/
│   │   ├── client.ts
│   │   ├── errors.ts
│   │   └── generated/
│   │       └── schema.d.ts
│   ├── components/
│   │   ├── app-shell.tsx
│   │   ├── async-state.tsx
│   │   ├── source-link.tsx
│   │   ├── platform-login-panel.tsx
│   │   ├── course-schedule-grid.tsx
│   │   ├── course-identity-mapping.tsx
│   │   ├── sync-status-badge.tsx
│   │   ├── health-badge.tsx
│   │   └── confirm-action.tsx
│   ├── features/
│   │   ├── setup/
│   │   ├── today/
│   │   ├── work-items/
│   │   ├── courses/
│   │   ├── projects/
│   │   ├── integrations/
│   │   └── settings/
│   ├── styles/
│   │   ├── tokens.css
│   │   └── global.css
│   ├── utils/
│   │   ├── datetime.ts
│   │   └── path.ts
│   └── main.tsx
├── tests/
│   ├── setup.ts
│   └── render-with-providers.tsx
├── e2e/
├── index.html
├── package.json
└── vite.config.ts
```

每个 feature 内按需要保持扁平结构：

```text
features/projects/
├── api.ts
├── keys.ts
├── types.ts
├── project-list-page.tsx
├── project-detail-page.tsx
├── project-form.tsx
├── project-status-form.tsx
├── project-status-history.tsx
├── project-health-panel.tsx
├── project-work-items.tsx
├── milestone-list.tsx
├── repository-card.tsx
└── *.test.tsx
```

只有被多个 feature 使用的组件才提升到 `src/components`。不要为单次操作预先创建通用 hooks、Repository 前端类或全局 store。

## 3. 应用入口与 Provider 顺序

```text
StrictMode
└── ConfigProvider（Ant Design 中文、主题、DatePicker 时区行为）
    └── QueryClientProvider
        └── RouterProvider
            └── AppShell / SetupPage
```

- `QueryClient` 在模块级创建一次。
- Ant Design 使用 `zh_CN` locale。
- 路由级错误边界展示可恢复错误，不让整个应用白屏。
- P0 不启用 Service Worker，不缓存敏感 API 响应。

## 4. 路由规范

### 4.1 路由表

| 路径 | 页面组件 | 数据依赖 | 说明 |
|---|---|---|---|
| `/setup` | `SetupPage` | bootstrap | 未完成初始化时可访问 |
| `/` | `TodayPage` | today | 默认首页 |
| `/inbox` | `WorkItemListPage` | work-items、courses、projects | 筛选进入 URL |
| `/courses` | `CourseListPage` | courses、identities、schedule | 统一课程、周课程表和待确认映射 |
| `/courses/:courseId` | `CourseDetailPage` | course、identities、schedule、work-items | 课程表和跨平台待办 |
| `/projects` | `ProjectListPage` | projects | 健康概览 |
| `/projects/:projectId` | `ProjectDetailPage` | project、snapshots | 项目处理中心 |
| `/settings/integrations` | `IntegrationsPage` | connections、sync-runs、github credential status | 同步中心 |
| `/settings` | `SettingsPage` | settings | 本地偏好 |
| `*` | `NotFoundPage` | 无 | 返回今日 |

### 4.2 路由规则

- 使用 `createBrowserRouter` 和路由级 `lazy`。
- `/setup` 不包在标准 AppShell 中，其余页面共用 AppShell。
- bootstrap 未完成时，业务路由统一重定向 `/setup`；完成后访问 `/setup` 重定向 `/`。
- ID 只允许 UUID 形式的路由参数；非法 ID 显示未找到，不发无意义请求。
- 列表筛选、分页、排序使用 `URLSearchParams`，不另存全局状态。
- 详情抽屉如需可分享，也使用查询参数，例如 `/inbox?item=<uuid>`。

## 5. API 客户端与类型

### 5.1 OpenAPI 类型生成

后端 OpenAPI 是接口类型唯一来源：

```bash
npm run generate:api
```

生成目标：`src/api/generated/schema.d.ts`。

- 生成文件不手工编辑。
- API 路径参数、请求体和响应体从 `paths`/`components` 类型提取。
- `features/*/types.ts` 只定义纯 UI 类型，例如表格行、表单值、健康颜色映射。
- 不在多个 feature 中手写同名 `WorkItem`、`Project` 接口。

### 5.2 fetch 封装

`api/client.ts` 只负责：

- 同源 `/api/v1` 前缀。
- JSON 编解码。
- 写请求添加 `Content-Type: application/json` 和 `X-Student-Workbench-Client`。
- 将后端错误体解析为 `ApiError`。
- 支持 `AbortSignal`。
- 204 响应不解析 JSON。

禁止：

- 在组件中散落 `fetch('/api/...')`。
- 将 token 放入 Authorization 或 localStorage。
- mutation 自动重试。
- 把原始 HTML、堆栈或 Cookie 展示到界面。

后端错误格式：

```ts
type ApiErrorBody = {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
    request_id: string
  }
}
```

## 6. 状态管理

### 6.1 状态分类

| 状态 | 存放位置 |
|---|---|
| 列表、详情、同步状态、设置 | TanStack Query |
| 当前筛选、页码、排序 | URL 查询参数 |
| 表单字段、弹窗开关、局部步骤 | React `useState`/AntD Form |
| 主题等少数本地 UI 偏好 | P0 可使用 localStorage，不含业务数据 |
| 跨页面业务全局 store | 不引入 |

### 6.2 QueryClient 默认值

- `staleTime: 15_000`。
- `refetchOnWindowFocus: false`，通过 mutation 失效和显式刷新保证一致。
- `refetchOnReconnect: true`。
- GET 仅对网络错误和 5xx 重试 1 次；4xx 不重试。
- mutation `retry: 0`。
- 已有数据时后台刷新保留 UI，不清空列表。

### 6.3 Query Key 规范

按资源集中定义：

```ts
export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (filters: ProjectFilters) => [...projectKeys.lists(), filters] as const,
  details: () => [...projectKeys.all, 'detail'] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
}
```

同样定义：

- `todayKeys`
- `workItemKeys`
- `courseKeys`
- `courseIdentityKeys`
- `scheduleKeys`
- `platformLoginKeys`
- `connectionKeys`
- `syncRunKeys`
- `settingsKeys`
- `bootstrapKeys`

Key 中只放可序列化值，查询前统一默认筛选值，避免 `{status: undefined}` 与缺字段形成两份缓存。

### 6.4 Mutation 失效关系

| 操作 | 必须失效的查询 |
|---|---|
| 新建/修改 WorkItem | today、work-items、相关 course、相关 project |
| 修改项目状态、原因或下一步 | projects、project detail、status history、today |
| 新增/修改项目待办 | projects、project detail、work-items、today |
| 修改里程碑 | projects、project detail、today |
| 教务同步完成 | courses、course identities、schedule、connections、sync-runs、today |
| 学习平台同步完成 | work-items、courses、course identities、connections、sync-runs、today |
| 课程身份映射变化 | courses、course identities、schedule、work-items、today |
| 仓库扫描/远端同步完成 | projects、project detail、sync-runs、today |
| 修改设置 | settings、today、projects |
| 完成首次引导 | bootstrap、today、connections、projects |

P0 对少量更新可使用失效后刷新；只有状态按钮等高频交互需要乐观更新。乐观更新必须先取消相关查询、保存快照，失败回滚，最终无论成败都失效查询。

### 6.5 同步轮询

- 创建同步后保存 `syncRunId`。
- 仅当状态为 `queued/running` 时 `refetchInterval: 1000`。
- 到达终态后停止轮询并执行对应失效。
- 页面离开时停止该页面的轮询，后端任务继续。
- 回到同步中心时，通过活动 SyncRun 重新附着，不重复创建。
- 收到 `409 SYNC_ALREADY_RUNNING` 时读取 `details.sync_run_id` 并附着。

## 7. 组件规范

### 7.1 组件分层

1. **Page**：组合数据查询和页面布局，不堆叠全部 JSX。
2. **Feature 组件**：实现教务/学习平台登录向导、课程映射、健康面板、里程碑列表等领域交互。
3. **共享组件**：只放通用反馈和展示组件。
4. **Ant Design 基础组件**：表单、表格、日期、对话框等。

页面组件不直接包含复杂健康推断、同步合并或时间计算规则。

### 7.2 必备共享组件

#### `AsyncState`

统一处理首次加载、空数据和请求失败；已有数据的后台错误由页面顶部提示，不用错误页替换旧数据。

#### `PlatformLoginPanel`

- 支持 `embedded/browser` 两种模式，默认内嵌。
- 根据后端登录状态展示账号密码、验证码挑战、等待、成功和外部浏览器回退。
- 密码和验证码只存在当前表单内存，提交后清空，不写入浏览器持久化存储。
- 不直接 iframe 加载平台网站，不读取平台 Cookie。

#### `CourseScheduleGrid`

- 按周展示教务课程表，课程条目不是待办。
- 点击统一课程进入课程详情；未关联身份显示映射入口，不伪造课程归属。

#### `CourseIdentityMapping`

- 展示外部课程名、来源平台、学期、教师和匹配状态。
- 唯一精确候选标注自动关联，歧义必须手动选择，不提供“模糊匹配合并全部”按钮。
- 支持关联已有课程、创建新课程、解除关联和忽略来源；统一课程可编辑 `term_start_date`（第一教学周周一），缺失时今日课程区域提示确认。

#### `HealthBadge`

- 输入后端返回的 `green/yellow/red/unknown/inactive`。
- 同时显示颜色、图标和中文文字。
- `unknown` 显示“数据不足”，不能显示为绿色；`inactive` 显示“无需评估”，不能显示为数据缺失。

#### `ProjectStatusBadge`

- 展示 `idea/planning/in_progress/blocked/waiting/on_hold/completed/cancelled/archived` 的中文名称。
- 对 `blocked/waiting/on_hold/cancelled` 同时展示具体 `status_reason`，不能只显示彩色标签。
- 生命周期状态和健康等级使用不同组件，不互相推导。

#### `SyncStatusBadge`

区分运行、成功、部分成功、失败、需登录、中断和数据过期。

#### `SourceLink`

- 显示来源平台和“新窗口打开”。
- 使用 `target="_blank" rel="noopener noreferrer"`。
- 无 `source_url` 时明确显示“无来源链接”，不生成猜测 URL。

### 7.3 表单

- 使用 AntD Form；不额外引入第二套表单状态库。
- 外部同步字段设为只读，并与“我的计划”分组；学习平台事项的课程归属通过 `CourseIdentityMapping` 调整，手动事项可直接选择课程。
- 项目 `blocked/waiting/on_hold/cancelled` 状态必须填写具体 `status_reason`；`waiting/on_hold` 可填写 `resume_at`。
- 项目待办表单复用 WorkItem 表单，创建时固定 `project_id/source_type=manual/item_type=task`，用户可设置标题、截止、计划、优先级和备注。
- `planned_end_at` 必须晚于 `planned_start_at`。
- 截止时间到分钟，目标日期使用日期；不要混用。
- 教务/学习平台登录提供“内嵌向导/外部浏览器”和“仅本次/保存密码”两组选择；选择保存时才打开本地账号密码对话框，提交后立即清空密码与验证码字段，之后只显示账号标识和 configured 状态。
- GitHub token 对话框提交后立即清空本地字段；平台密码和 token 均不得进入浏览器持久化存储。

## 8. 样式与视觉规范

- 使用 Ant Design token 配置主色、文字、边框、状态和圆角。
- 页面特定布局使用 CSS Modules 或 feature 内样式文件；不同时引入 Tailwind、styled-components。
- 桌面优先，建议内容最大宽度 1440px；窄屏允许侧栏折叠，但 P0 不做完整移动端。
- 今日页优先展示行动信息，避免无意义的大面积图表。
- 项目健康原因以列表为主，不用雷达图或生产力分数。
- 时间显示“绝对时间 + 相对说明”，例如“11 月 25 日 23:59（2 天后）”。
- 过期数据使用显著但不过度警报的提示，避免所有页面都变红。

## 9. 日期与时区

- API 只传带时区的 ISO 8601 字符串，日期字段传 `YYYY-MM-DD`。
- 后端存 UTC；前端使用设置中的 IANA 时区解释“今天”和“逾期”。
- AntD DatePicker 使用其兼容的 Day.js；Day.js 必须作为直接依赖声明并锁定。
- `datetime.ts` 集中处理 ISO 与表单值互转、相对时间和日期边界。
- 不用浏览器本地 `YYYY-MM-DD HH:mm:ss` 非标准字符串构造 Date。
- 前端不自行决定健康等级，只负责展示后端结果。

## 10. 错误处理与交互反馈

| 场景 | 前端行为 |
|---|---|
| 首次 GET 失败且无缓存 | AsyncState 显示错误与重试 |
| 后台刷新失败且有缓存 | 保留数据，显示“更新失败，当前为上次数据” |
| `needs_auth` | 提供重新登录按钮，不只显示失败 |
| `SYNC_ALREADY_RUNNING` | 附着现有运行，不重复启动 |
| 外部 API 限流 | 显示可理解摘要与最后成功时间 |
| 本地 mutation 失败 | 表单内容保留，显示服务端字段错误 |
| 断网 | 本地 API 可用时继续工作；外部同步失败不阻断本地编辑 |

成功提示必须具体，例如“已同步 18 项，新增 2 项”，而不是统一“操作成功”。

## 11. 测试规范

### 11.1 单元与组件测试

使用 Vitest + Testing Library，测试用户可观察行为：

- HealthBadge 五种等级的文字与可访问名称，inactive 与 unknown 不混淆。
- WorkItem 表单区分截止和计划时间。
- `blocked/waiting/on_hold/cancelled` 项目缺少原因时不能提交，状态保存后历史区追加记录。
- 项目待办从详情页创建后自动关联项目，并刷新详情、收件箱和今日查询。
- 保存平台密码后密码字段被清空，页面只保留 configured 和账号标识。
- 课程映射只对唯一精确候选自动关联，歧义保持待确认；改绑后课程表、收件箱和今日课程一起刷新。
- mutation 成功后失效正确查询。
- 同步只在运行态轮询，终态后停止。
- 已有数据时后台请求失败不清空页面。
- `409 SYNC_ALREADY_RUNNING` 能附着现有任务。

API mock 使用 `vi.stubGlobal('fetch', ...)` 或 feature API mock；P0 不为少量请求额外引入完整 mock server。

### 11.2 E2E

使用 `@playwright/test`，连接真实 FastAPI + 临时 SQLite + `academic_fake` + `learning_fake`：

1. 首次引导 → 教务 fake 同步课程表 → 学习 fake 同步作业 → 确认课程关联 → 今日课程定位待办 → 今日计划。
2. 创建项目 → 关联临时 Git 仓库 → 扫描 → 健康原因定位。
3. fake 平台会话过期 → 内嵌或外部重新登录 → 本地计划和课程映射保持。
4. 同步期间切换页面 → 返回后可重新附着。
5. 项目改为 waiting/blocked → 填写原因 → 查看状态历史 → 新增项目待办并计划今天 → 今日页完成。

E2E 不访问真实教务/学习平台账号，不读取开发者个人数据库。

### 11.3 测试代码约束

- 优先 `getByRole`、`getByLabel`，避免脆弱 CSS 选择器。
- 不用固定 `sleep` 等待页面，使用可观察条件和 Playwright 自动等待。
- 每个测试独立 QueryClient、数据库和临时目录。
- 不用快照测试替代行为断言。

## 12. 前端完成检查

- `typecheck`、lint、单元测试和 E2E 全部通过。
- 所有路由具备加载、空、错误状态。
- 所有 P0 操作可通过键盘完成。
- 无平台密码、验证码、平台 Cookie、GitHub token 或业务数据库进入浏览器持久化存储。
- 无手写的第二套健康规则、教务/学习同步归并逻辑或课程映射规则。
- OpenAPI 类型已更新且生成文件无手工修改。
