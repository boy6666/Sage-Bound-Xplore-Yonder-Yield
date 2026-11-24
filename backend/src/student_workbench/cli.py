from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path


def _serve() -> None:
    import uvicorn

    from .main import create_app

    host = os.environ.get("STUDENT_WORKBENCH_HOST", "127.0.0.1")
    port = int(os.environ.get("STUDENT_WORKBENCH_PORT", "8765"))
    uvicorn.run(create_app(), host=host, port=port)


def _academic_sync(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from . import models  # noqa: F401  (registers ORM metadata)
    from .adapters.academic_portal_v1 import capture_schedule_html, default_profile_dir
    from .adapters.kb_parser import parse_kb_html
    from .config import AppConfig
    from .db import Base, create_db_engine, create_session_factory
    from .models import Connection
    from .services.academic_import import import_schedule

    config = AppConfig.from_env()
    config.ensure_data_dir()
    engine = create_db_engine(config.resolved_db_url)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)

    with factory() as session:
        connection = None
        if args.connection_id:
            connection = session.get(Connection, args.connection_id)
            if connection is None:
                print(f"连接不存在: {args.connection_id}")
                return 2
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

    profile_dir = Path(args.profile) if args.profile else default_profile_dir(config.data_dir)
    print("即将打开浏览器窗口，请完成登录（账号、密码、验证码）。")
    print(f"浏览器资料目录: {profile_dir}")
    print(f"最长等待 {args.timeout} 秒，登录成功后会自动打开课程表并保存。")

    try:
        html = asyncio.run(
            capture_schedule_html(
                profile_dir,
                timeout_seconds=args.timeout,
                headless=args.headless,
            )
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as text
        print(f"抓取失败: {exc}")
        return 1

    if args.save_html:
        saved = Path(args.save_html)
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
    print(f"数据库: {config.resolved_db_url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workbench", description="Student Workbench")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="启动本地服务")

    academic = subparsers.add_parser("academic", help="教务平台相关操作")
    academic_sub = academic.add_subparsers(dest="action")
    sync = academic_sub.add_parser("sync", help="登录教务并导入课程表")
    sync.add_argument("--connection-id", default=None)
    sync.add_argument("--display-name", default="教务系统")
    sync.add_argument("--profile", default=None, help="浏览器资料目录")
    sync.add_argument("--save-html", default=None, help="把抓到的课表页面另存为文件")
    sync.add_argument("--timeout", type=int, default=600, help="等待登录的秒数")
    sync.add_argument("--headless", action="store_true", help="无头模式（无法手动登录）")

    return parser


def main(argv: list[str] | None = None) -> int | None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "academic" and getattr(args, "action", None) == "sync":
        return _academic_sync(args)

    _serve()
    return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())