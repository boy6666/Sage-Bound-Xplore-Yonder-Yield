from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path


def _serve() -> None:
    import uvicorn

    from .main import create_app

    host = os.environ.get("STUDENT_WORKBENCH_HOST", "127.0.0.1")
    port = int(os.environ.get("STUDENT_WORKBENCH_PORT", "8765"))
    uvicorn.run(create_app(), host=host, port=port)


def _session_factory():
    from sqlalchemy import select

    from . import models  # noqa: F401  (registers ORM metadata)
    from .config import AppConfig
    from .db import Base, create_db_engine, create_session_factory
    from .migrations import ensure_schema

    config = AppConfig.from_env()
    config.ensure_data_dir()
    config.apply_runtime_env()
    engine = create_db_engine(config.resolved_db_url)
    Base.metadata.create_all(engine)
    ensure_schema(engine)
    print(f"数据库: {config.resolved_db_url}")
    return config, create_session_factory(engine), select


def _academic_connection(factory, select, args) -> str | None:
    from .models import Connection

    with factory() as session:
        connection = None
        if args.connection_id:
            connection = session.get(Connection, args.connection_id)
            if connection is None:
                print(f"连接不存在: {args.connection_id}")
                return None
        else:
            connection = session.scalar(
                select(Connection)
                .where(Connection.provider == "academic_portal_v1")
                .order_by(Connection.created_at)
                .limit(1)
            )
        if connection is None:
            connection = Connection(
                kind="academic",
                provider="academic_portal_v1",
                display_name=args.display_name,
                status="needs_auth",
            )
            session.add(connection)
            session.flush()
        connection_id = connection.id
        session.commit()
    return connection_id


def _import_html(factory, connection_id: str, html: str, save_html: str | None) -> int:
    from .adapters.kb_parser import parse_kb_html
    from .models import Connection
    from .services.academic_import import import_schedule

    if save_html:
        saved = Path(save_html)
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(html, encoding="utf-8")
        print(f"已保存页面: {saved}")

    parsed = parse_kb_html(html)
    with factory() as session:
        connection = session.get(Connection, connection_id)
        result = import_schedule(session, connection, parsed)
        session.commit()

    print(f"学期: {parsed.term_label or '未知'}")
    print(
        "导入结果: "
        f"课程 {result['courses']} 门（新建 {result['created_courses']}），"
        f"身份 {result['created_identities']} 个，"
        f"课程表 {result['entries']} 条（移除 {result['removed_entries']}）"
    )
    return 0


def _academic_login(args: argparse.Namespace) -> int:
    from .adapters.academic_portal_v1 import capture_schedule_html, default_profile_dir
    from .adapters.portal_session import save_cookies

    config, factory, select = _session_factory()
    connection_id = _academic_connection(factory, select, args)
    if connection_id is None:
        return 2

    profile_dir = Path(args.profile) if args.profile else default_profile_dir(config.data_dir)
    print("即将打开浏览器窗口，请完成登录（账号、密码、验证码）。")
    print(f"浏览器资料目录: {profile_dir}")
    print(f"最长等待 {args.timeout} 秒。登录成功后会自动抓取课表并保存登录 Cookie。")

    try:
        html, cookies = asyncio.run(
            capture_schedule_html(
                profile_dir,
                timeout_seconds=args.timeout,
                headless=args.headless,
            )
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as text
        print(f"登录/抓取失败: {exc}")
        return 1

    saved_at = datetime.now().astimezone().isoformat(timespec="seconds")
    cookie_file = save_cookies(config.data_dir, cookies, saved_at)
    print(f"已保存登录 Cookie: {cookie_file}（仅本机，添加在 .gitignore 的 data/ 下）")

    return _import_html(factory, connection_id, html, args.save_html)


def _academic_sync(args: argparse.Namespace) -> int:
    from .adapters.academic_http import fetch_schedule_html
    from .adapters.portal_session import load_cookies, to_httpx_cookies

    config, factory, select = _session_factory()
    connection_id = _academic_connection(factory, select, args)
    if connection_id is None:
        return 2

    stored = load_cookies(config.data_dir)
    if stored is None:
        print("没有可用的登录会话，请先运行一次：workbench academic login")
        return 1

    print(f"使用本地保存的 Cookie（{stored.saved_at}）直接请求课表页…")
    try:
        html = fetch_schedule_html(to_httpx_cookies(stored.cookies))
    except Exception as exc:  # noqa: BLE001
        print(f"请求失败: {exc}")
        return 1

    if not html:
        print("登录会话已失效，请重新运行一次：workbench academic login")
        return 1

    return _import_html(factory, connection_id, html, args.save_html)


def _academic_adjustments(args: argparse.Namespace) -> int:
    from .adapters.academic_http import fetch_adjustments_html
    from .adapters.adjustments_parser import parse_adjustments_html
    from .adapters.portal_session import load_cookies, to_httpx_cookies
    from .models import Connection
    from .services.academic_import import import_adjustments

    config, factory, select = _session_factory()
    connection_id = _academic_connection(factory, select, args)
    if connection_id is None:
        return 2

    stored = load_cookies(config.data_dir)
    if stored is None:
        print("没有可用的登录会话，请先运行一次：workbench academic login")
        return 1

    print("使用本地保存的 Cookie 请求调停补课页…")
    try:
        html = fetch_adjustments_html(to_httpx_cookies(stored.cookies))
    except Exception as exc:  # noqa: BLE001
        print(f"请求失败: {exc}")
        return 1
    if not html:
        print("登录会话已失效，请重新运行一次：workbench academic login")
        return 1

    if args.save_html:
        saved = Path(args.save_html)
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(html, encoding="utf-8")
        print(f"已保存页面: {saved}")

    parsed = parse_adjustments_html(html)
    with factory() as session:
        connection = session.get(Connection, connection_id)
        result = import_adjustments(session, connection, parsed)
        session.commit()

    print(f"学期: {parsed.term_label or '未知'}")
    print(
        f"调停补课: {result['records']} 条"
        f"（新增 {result['created']}，移除 {result['removed']}）"
    )
    return 0


def _academic_logout(args: argparse.Namespace) -> int:
    from .adapters.portal_session import clear_cookies, cookie_path

    config, _factory, _select = _session_factory()
    removed = clear_cookies(config.data_dir)
    if removed:
        print("已删除本地 Cookie")
    else:
        print(f"没有找到 Cookie 文件: {cookie_path(config.data_dir)}")
    return 0


def _browser_install(args: argparse.Namespace) -> int:
    import shutil
    import subprocess
    import sys

    from .config import AppConfig

    config = AppConfig.from_env()
    config.ensure_data_dir()
    target = config.apply_runtime_env()
    print(f"浏览器安装目录: {target}")

    executable = shutil.which("playwright")
    if executable:
        command = [executable, "install", "chromium"]
    else:
        command = [sys.executable, "-m", "playwright", "install", "chromium"]

    result = subprocess.run(
        command,
        env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(target)},
        check=False,
    )
    if result.returncode == 0:
        print("Chromium 安装完成")
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workbench", description="Student Workbench")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="启动本地服务")

    academic = subparsers.add_parser("academic", help="教务平台相关操作")
    academic_sub = academic.add_subparsers(dest="action")

    login = academic_sub.add_parser("login", help="打开浏览器登录一次，保存会话 Cookie 并导入课表")
    login.add_argument("--connection-id", default=None)
    login.add_argument("--display-name", default="教务系统")
    login.add_argument("--profile", default=None, help="浏览器资料目录")
    login.add_argument("--save-html", default=None, help="把抓到的课表页面另存为文件")
    login.add_argument("--timeout", type=int, default=600, help="等待登录的秒数")
    login.add_argument("--headless", action="store_true", help="无头模式（无法手动登录）")

    sync = academic_sub.add_parser("sync", help="用已保存的 Cookie 直接抓取课表（不打开浏览器）")
    sync.add_argument("--connection-id", default=None)
    sync.add_argument("--display-name", default="教务系统")
    sync.add_argument("--save-html", default=None)

    adjustments = academic_sub.add_parser(
        "adjustments", help="用已保存的 Cookie 抓取调停补课记录（不打开浏览器）"
    )
    adjustments.add_argument("--connection-id", default=None)
    adjustments.add_argument("--display-name", default="教务系统")
    adjustments.add_argument("--save-html", default=None)

    academic_sub.add_parser("logout", help="删除本地保存的登录 Cookie")

    browser = subparsers.add_parser("browser", help="浏览器依赖")
    browser_sub = browser.add_subparsers(dest="browser_action")
    browser_sub.add_parser(
        "install", help="把 Chromium 安装到项目 data/ms-playwright（不占 C 盘）"
    )

    return parser


def main(argv: list[str] | None = None) -> int | None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "academic":
        action = getattr(args, "action", None)
        if action == "login":
            return _academic_login(args)
        if action == "sync":
            return _academic_sync(args)
        if action == "adjustments":
            return _academic_adjustments(args)
        if action == "logout":
            return _academic_logout(args)
        parser.parse_args(["academic", "--help"])

    if args.command == "browser":
        if getattr(args, "browser_action", None) == "install":
            return _browser_install(args)
        parser.parse_args(["browser", "--help"])

    _serve()
    return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())