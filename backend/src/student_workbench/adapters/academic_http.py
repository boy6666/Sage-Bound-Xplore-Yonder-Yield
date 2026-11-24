"""Fetch the schedule page over plain HTTP, reusing the cookie from a real login."""

from __future__ import annotations

import httpx

DEFAULT_KB_URL = "http://jw.xujc.com/student/index.php?c=Default&a=Kb"
DEFAULT_TBK_URL = "http://jw.xujc.com/student/index.php?c=Default&a=tbk"
DEFAULT_LOGIN_URL = "http://jw.xujc.com/student/index.php"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

LOGIN_MARKER = 'id="loginbtn"'
SCHEDULE_MARKER = 'class="data small solid"'

STATE_OK = "ok"
STATE_LOGIN = "login"
STATE_UNKNOWN = "unknown"


def classify(html: str) -> str:
    if LOGIN_MARKER in html:
        return STATE_LOGIN
    if SCHEDULE_MARKER in html or "table" in html and "solid" in html:
        return STATE_OK
    return STATE_UNKNOWN


def _fetch(
    url: str,
    cookie_jar: dict[str, str],
    *,
    login_url: str,
    timeout: float,
) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": login_url,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    with httpx.Client(
        cookies=cookie_jar,
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def fetch_schedule_html(
    cookie_jar: dict[str, str],
    *,
    kb_url: str = DEFAULT_KB_URL,
    login_url: str = DEFAULT_LOGIN_URL,
    timeout: float = 25.0,
) -> str:
    """Return the schedule page HTML, or ``""`` when the session is no longer valid."""
    html = _fetch(kb_url, cookie_jar, login_url=login_url, timeout=timeout)
    if classify(html) == STATE_LOGIN:
        return ""
    return html


def fetch_adjustments_html(
    cookie_jar: dict[str, str],
    *,
    tbk_url: str = DEFAULT_TBK_URL,
    login_url: str = DEFAULT_LOGIN_URL,
    timeout: float = 25.0,
) -> str:
    """Return the 调停补课 page HTML, or ``""`` when the session is no longer valid."""
    html = _fetch(tbk_url, cookie_jar, login_url=login_url, timeout=timeout)
    if LOGIN_MARKER in html:
        return ""
    return html