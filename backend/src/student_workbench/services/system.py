from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Course, Project, WorkItem
from ..timeutil import local_today
from .dashboard import classify_items
from .settings import current_tz, get_settings_row


def bootstrap_payload(session: Session) -> dict:
    settings_row = get_settings_row(session)
    tz = current_tz(session)
    today = local_today(tz)
    groups = classify_items(session, today, tz, settings_row.upcoming_days)
    inbox = session.scalar(
        select(func.count()).select_from(WorkItem).where(WorkItem.status == "inbox")
    )
    projects = session.scalar(select(func.count()).select_from(Project))
    courses = session.scalar(select(func.count()).select_from(Course))
    return {
        "setup_completed": settings_row.setup_completed,
        "timezone": settings_row.timezone,
        "today": today.isoformat(),
        "counts": {
            "inbox": int(inbox or 0),
            "today": len(groups["overdue"]) + len(groups["today_planned"]),
            "projects": int(projects or 0),
            "courses": int(courses or 0),
        },
    }
