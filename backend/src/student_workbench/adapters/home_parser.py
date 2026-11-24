"""Read the teaching week that the academic portal renders on its home page."""

from __future__ import annotations

import re

_WEEK_PATTERN = re.compile(r"本学期第\s*(\d+)\s*周")


def parse_current_week(html: str) -> int | None:
    """Return the week shown by the portal, or ``None`` when it is absent."""
    match = _WEEK_PATTERN.search(html)
    if match is None:
        return None
    week = int(match.group(1))
    return week if week > 0 else None
