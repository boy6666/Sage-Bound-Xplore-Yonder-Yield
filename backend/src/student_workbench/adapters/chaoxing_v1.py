"""HTTP access to 超星/学习通, reusing the cookie from a browser login.

Only the "我的作业" aggregate page is read. It returns every assignment across
courses in one request, which keeps the request count low. Deadlines are not part
of that page, so they are intentionally left empty for the user to fill in.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

ALL_TASK_URL = "https://mooc1-api.chaoxing.com/mooc-ans/mooc2/work/all-task"
HOME_URL = "https://i.chaoxing.com"
LOGIN_HOST = "passport2.chaoxing.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class ChaoxingError(RuntimeError):
    """Base error for 超星 capture failures."""


class ChaoxingDependencyMissing(ChaoxingError):
    """Playwright or its browser binary is not installed."""


class ChaoxingAuthRequired(ChaoxingError):
    """The saved cookie no longer opens the assignment page."""


class ChaoxingStructureChanged(ChaoxingError):
    """The assignment page was returned but does not look like the expected one."""


def default_profile_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "browser" / "chaoxing"


def fetch_all_task_html(
    cookie_jar: dict[str, str],
    *,
    url: str = ALL_TASK_URL,
    timeout: float = 25.0,
) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": HOME_URL,
    }
    with httpx.Client(
        cookies=cookie_jar,
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    if LOGIN_HOST in str(response.url):
        return ""
    html = response.text
    if "我的作业" not in html:
        raise ChaoxingStructureChanged("作业聚合页结构不符合预期，可能已改版")
    return html


async def capture_cookies_after_login(
    profile_dir: Path,
    *,
    timeout_seconds: int = 600,
) -> list[dict]:
    """Open the login page and wait until the user finishes logging in."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise ChaoxingDependencyMissing(
            "未安装 Playwright，无法打开浏览器登录学习通；请在 backend 目录运行 uv sync"
        ) from exc

    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        try:
            context = await playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                no_viewport=True,
                channel="chromium",
            )
        except Exception as exc:  # noqa: BLE001 - missing browser binary
            raise ChaoxingDependencyMissing(
                "未找到可用的 Chromium。请在 backend 目录运行 "
                "python -m student_workbench.cli browser install"
            ) from exc

        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(HOME_URL, wait_until="load", timeout=90_000)

            waited = 0.0
            while waited < timeout_seconds:
                await asyncio.sleep(2)
                waited += 2
                if page.is_closed():
                    raise ChaoxingAuthRequired("登录窗口已关闭，未完成登录")
                if LOGIN_HOST not in page.url:
                    return await context.cookies()
            raise ChaoxingAuthRequired(
                "等待登录超时：请在打开的浏览器窗口完成登录后重试"
            )
        finally:
            try:
                await context.close()
            except Exception:  # noqa: BLE001
                pass