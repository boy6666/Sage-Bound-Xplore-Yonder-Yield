@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo   Student Workbench 一键启动
echo   当前目录: %CD%
echo ==================================================
echo.

where uv >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 uv，请先安装：https://docs.astral.sh/uv/
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 npm，请先安装 Node.js
  pause
  exit /b 1
)

if not exist "backend\.venv" (
  echo [准备] 首次运行，安装后端依赖...
  pushd backend
  call uv sync
  popd
)

if not exist "frontend\node_modules" (
  echo [准备] 首次运行，安装前端依赖...
  pushd frontend
  call npm install
  popd
)

netstat -ano | findstr ":8765" | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo [跳过] 8765 已被占用，后端可能已在运行
) else (
  echo [启动] 后端 http://127.0.0.1:8765
  start "workbench-backend" cmd /k "cd backend && uv run uvicorn student_workbench.asgi:app --port 8765"
)

netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if not errorlevel 1 (
  echo [跳过] 5173 已被占用，前端可能已在运行
) else (
  echo [启动] 前端 http://127.0.0.1:5173
  start "workbench-frontend" cmd /k "cd frontend && npm run dev"
)

echo.
echo 完成。关闭对应窗口即可停止服务。
echo 前端地址: http://127.0.0.1:5173
echo.
pause
