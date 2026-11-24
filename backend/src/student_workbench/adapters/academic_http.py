"""Fetch the schedule page over plain HTTP, reusing the cookie from a real login."""

from __future__ import annotations

import httpx

DEFAULT_KB_URL = "http://jw.xujc.com/student/index.php?c=Default&a=Kb"
DEFAULT_TBK_URL = "http://jw.xujc.com/student/index.php?c=Default&a=tbk"
DEFAULT_LOGIN_URL = "http://jw.xujc.com/student/index.php"
DEFAULT_HOME_URL = "http://jw.xujc.com/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

LOGIN_MARKER = 'id="loginbtn"'
REFUSAL_MARKER = "拒绝访问该页面"
SCHEDULE_MARKER = 'class="data small solid"'

STATE_OK = "ok"
STATE_LOGIN = "login"
STATE_UNKNOWN = "unknown"


class ScheduleStructureChanged(RuntimeError):
    """The response is neither a timetable nor a login/refusal page."""


def classify(html: str) -> str:
    if LOGIN_MARKER in html or REFUSAL_MARKER in html:
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
    referer: str | None = None,
) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    effective_referer = login_url if referer is None else referer
    if effective_referer:
        headers["Referer"] = effective_referer
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
    """Return the schedule page HTML, or ``""`` when the session is no longer valid.

    A refusal page (the portal answers 200 with a 403 notice for stale sessions)
    counts as "session invalid", not as a parsed timetable. Anything that is
    neither a timetable nor a login page raises ``ScheduleStructureChanged`` so
    the UI can tell "expired login" apart from "the site changed".
    """
    html = _fetch(kb_url, cookie_jar, login_url=login_url, timeout=timeout)
    state = classify(html)
    if state == STATE_LOGIN:
        return ""
    if state != STATE_OK:
        raise ScheduleStructureChanged("课表页面结构不符合预期，可能已改版")
    return html


def fetch_home_html(
    cookie_jar: dict[str, str],
    *,
    home_url: str = DEFAULT_HOME_URL,
    login_url: str = DEFAULT_LOGIN_URL,
    timeout: float = 15.0,
) -> str:
    """Return the portal home page HTML.

    The home page always renders a login button, so its presence does not mean the
    session expired. Callers detect expiry by failing to find the week marker.
    Sending a ``Referer`` makes the server return a different shell page without
    the week block, so this request deliberately omits it.
    """
    return _fetch(
        home_url, cookie_jar, login_url=login_url, timeout=timeout, referer=""
    )


def fetch_adjustments_html(
    cookie_jar: dict[str, str],
    *,
    tbk_url: str = DEFAULT_TBK_URL,
    login_url: str = DEFAULT_LOGIN_URL,
    timeout: float = 25.0,
) -> str:
    """Return the 调停补课 page HTML, or ``""`` when the session is no longer valid."""
    html = _fetch(tbk_url, cookie_jar, login_url=login_url, timeout=timeout)
    if LOGIN_MARKER in html or REFUSAL_MARKER in html:
        return ""
    return html