"""Academic portal adapter for 厦门大学嘉庚学院 综合教务系统 (jw.xujc.com).

The portal drops its session cookie when the browser closes, so login and the
schedule capture must happen in one browser session. Login is a real form with a
click-through captcha, so the user completes it manually in a visible window;
this adapter only waits for the logged-in menu, opens the schedule page and
returns its HTML. Parsing lives in :mod:`student_workbench.adapters.kb_parser`.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_LOGIN_URL = "http://jw.xujc.com/student/index.php"
DEFAULT_KB_URL = "http://jw.xujc.com/student/index.php?c=Default&a=Kb"

LOGGED_IN_SELECTOR = "a[href*='a=logout']"
SCHEDULE_TABLE_SELECTOR = "table.solid"


class PortalError(RuntimeError):
    """Base error for portal capture failures."""


class PortalAuthRequired(PortalError):
    """The user did not finish logging in before the timeout."""


class PortalStructureChanged(PortalError):
    """The schedule table was not found after login."""


def default_profile_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "browser" / "academic-portal"


async def capture_schedule_html(
    profile_dir: Path,
    *,
    login_url: str = DEFAULT_LOGIN_URL,
    kb_url: str = DEFAULT_KB_URL,
    timeout_seconds: int = 600,
    headless: bool = False,
) -> tuple[str, list[dict]]:
    """Open the portal, wait for a manual login, then return the schedule HTML and cookies."""
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeout
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise PortalError(
            "未安装 playwright，无法使用浏览器抓取教务课表；请先安装该依赖"
        ) from exc

    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(profile_dir), headless=headless, no_viewport=True
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(login_url, wait_until="load", timeout=60_000)

            try:
                await page.wait_for_selector(
                    LOGGED_IN_SELECTOR, timeout=timeout_seconds * 1000
                )
            except PlaywrightTimeout as exc:
                raise PortalAuthRequired(
                    "等待登录超时：请在打开的浏览器窗口完成登录（含验证码）后重试"
                ) from exc

            await page.goto(kb_url, wait_until="load", timeout=60_000)
            try:
                await page.wait_for_selector(SCHEDULE_TABLE_SELECTOR, timeout=60_000)
            except PlaywrightTimeout as exc:
                if await page.query_selector("#loginbtn"):
                    raise PortalAuthRequired("会话已失效，请重新登录") from exc
                raise PortalStructureChanged(
                    "未找到课程表表格，页面结构可能已变化"
                ) from exc

            await page.wait_for_timeout(1500)
            html = await page.content()
            cookies = await context.cookies()
            return html, cookies
        finally:
            await context.close()