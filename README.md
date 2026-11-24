# Student Workbench

本地优先的学生开发者工作台：把教务课程表、学习平台作业、GitHub/本地仓库状态和项目待办收进同一个执行视图。

仓库名沿用 `Sage-Bound-Xplore-Yonder-Yield`，产品代号为 **Student Workbench**。

## 当前状态

P0 已实现并通过测试：后端 81 项 pytest、前端 31 项 Vitest，`npm run build` 通过；
端到端冒烟覆盖引导、项目状态与原因校验、课程映射、fake 平台同步、今日聚合与来源校验。

尚未实现（按设计保留）：真实教务/学习平台适配器（`academic_portal_v1`、`chaoxing_v1` 返回
`PLATFORM_NOT_CONFIGURED`）、GitHub 远端同步、自动同步、周报与 AI 复盘。

## 目录结构

```text
.
├── docs/          # 产品、流程、架构、契约与实施文档
├── backend/       # FastAPI + SQLite 本地服务（Python 3.13）
├── frontend/      # React + TypeScript PWA（Vite）
└── tmp/           # 临时脚本与实验代码，已 git 忽略，不进入版本库
```

## 文档索引

| 文件 | 内容 |
|---|---|
| `docs/PRD.md` | 用户故事、P0/P1/P2 优先级、功能边界、验收场景 |
| `docs/APP_FLOW.md` | 首次引导、平台登录与同步、项目健康、今日执行流程 |
| `docs/TECH_STACK.md` | 技术选型、版本基线、部署与安全设计 |
| `docs/FRONTEND_GUIDELINES.md` | 路由、组件、状态管理与前端测试规范 |
| `docs/BACKEND_STRUCTURE.md` | 数据模型、健康规则、适配器契约、REST API |
| `docs/IMPLEMENTATION_PLAN.md` | 分阶段实施计划与 TDD 清单 |
| `docs/CONTRACT_SLICE.md` | **前后端共享接口契约（实现以本文件为准）** |

## 开发约定

1. 前后端独立开发，只通过 `docs/CONTRACT_SLICE.md` 定义的 `/api/v1` 契约交互。
2. TDD：先写失败测试，再写实现，最后重构。
3. 临时脚本、一次性迁移脚本、调试代码一律放 `tmp/`，不提交。
4. 不提交数据库文件、凭据、浏览器会话与日志。

## 本地运行

```bash
# 后端
cd backend
uv sync
uv run pytest -q
uv run uvicorn student_workbench.asgi:app --port 8765

# 前端
cd frontend
npm install
npm run test -- --run
npm run dev
```

前端开发服务器将 `/api` 代理到 `http://127.0.0.1:8765`。

## 导入真实教务课表

教务登录带验证码，必须人工完成一次；登录后的 Cookie 会保存到本机，之后同步走纯 HTTP，不再打开浏览器。

```bash
cd backend

# 只有第一次（或会话过期后）需要：登录一次并保存 Cookie
PYTHONPATH=src python -m student_workbench.cli academic login

# 日常同步：不打开浏览器，用已保存的 Cookie 直接抓课表
PYTHONPATH=src python -m student_workbench.cli academic sync

# 抓取调停补课记录（同样不打开浏览器，单独一次请求）
PYTHONPATH=src python -m student_workbench.cli academic adjustments

# 需要作废本机保存的登录状态时
PYTHONPATH=src python -m student_workbench.cli academic logout
```

`academic sync` 在会话失效时会明确提示重新执行 `academic login`，不会静默失败。同一学期重复执行是幂等的：条目按 external_id 更新，页面中已消失的条目会被移除。

Cookie 保存在应用数据目录 `cookies/academic_portal_v1.json`，不进入仓库、不写日志。

解析的是课表网格（`?c=Default&a=Kb`）：表头用 `colspan` 表达周二、周四各占两列，课程格用 `<br>` 分隔“课程名 / 教师 / 教室 / 周次”，单双周与跨节次（`rowspan`）都会被展开。

调停补课页（`?c=Default&a=tbk`）有“调停课”和“补课”两张表，空表显示“当前没有记录”。导入后今日页会叠加显示：

- 被停课的课程标为 `已停课` 并加删除线；
- 被调课的课程标为 `已调课`；
- 当天补课的课程会作为额外条目出现，时间由课表页的节次时间换算。

匹配规则是“课程名 + 周次 + 星期”，同一天同一门课有多节时会被一并标记；这是当前已知的精度限制。

界面里的“同步”按钮暂不支持教务平台，会提示改用上面的命令；学习平台仍走 `learning_fake` 流程。
