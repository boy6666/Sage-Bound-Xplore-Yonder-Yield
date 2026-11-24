"""Persist the academic portal session cookie locally.

The portal sets a browser-session cookie, which a browser drops when the window
closes. Keeping the cookie value lets ordinary HTTP requests reuse the same
server-side session, so the user only logs in when the session actually expires.

Cookies are credentials: they live under the app data directory (never in the
repository), are written with owner-only permissions where supported, and are
never logged.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

COOKIE_FILENAME = "academic_portal_v1.json"


@dataclass(frozen=True)
class StoredCookies:
    saved_at: str
    cookies: list[dict]


def cookie_path(data_dir: Path, provider: str = "academic_portal_v1") -> Path:
    return Path(data_dir) / "cookies" / f"{provider}.json"


def save_cookies(
    data_dir: Path,
    cookies: list[dict],
    saved_at: str,
    provider: str = "academic_portal_v1",
) -> Path:
    path = cookie_path(data_dir, provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": saved_at, "cookies": cookies}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:  # pragma: no cover - best effort on Windows
        pass
    return path


def load_cookies(
    data_dir: Path, provider: str = "academic_portal_v1"
) -> StoredCookies | None:
    path = cookie_path(data_dir, provider)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    cookies = payload.get("cookies")
    if not isinstance(cookies, list) or not cookies:
        return None
    return StoredCookies(saved_at=str(payload.get("saved_at", "")), cookies=cookies)


def to_httpx_cookies(cookies: list[dict]) -> dict[str, str]:
    jar: dict[str, str] = {}
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value is not None:
            jar[str(name)] = str(value)
    return jar


def clear_cookies(data_dir: Path, provider: str = "academic_portal_v1") -> bool:
    path = cookie_path(data_dir, provider)
    if path.exists():
        try:
            path.unlink()
            return True
        except OSError:
            return False
    return False