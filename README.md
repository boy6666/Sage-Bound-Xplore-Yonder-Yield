# Student Workbench

本地优先的学生开发者工作台：把教务课程表、学习平台作业、GitHub/本地仓库状态和项目待办收进同一个执行视图。

仓库名沿用 `Sage-Bound-Xplore-Yonder-Yield`，产品代号为 **Student Workbench**。

## 当前状态

设计与实施文档已完成；代码按前后端分离、TDD 方式实现中。

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
uv run uvicorn student_workbench.main:app --port 8765

# 前端
cd frontend
npm install
npm run test -- --run
npm run dev
```

前端开发服务器将 `/api` 代理到 `http://127.0.0.1:8765`。
