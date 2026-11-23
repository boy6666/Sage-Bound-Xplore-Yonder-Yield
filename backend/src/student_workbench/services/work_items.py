from __future__ import annotations

from collections.abc import Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from ..errors import AppError
from ..models import Course, Project, WorkItem
from ..schemas import WorkItemCreate, WorkItemUpdate
from ..timeutil import as_utc, iso, utcnow
from .settings import current_tz

ACTIVE_STATUSES = ("inbox", "planned", "in_progress")
DATETIME_FIELDS = ("due_at", "planned_start_at", "planned_end_at")
REQUIRED_FIELDS = ("title", "item_type", "priority", "status")


def get_item(session: Session, item_id: str) -> WorkItem:
    item = session.get(WorkItem, item_id)
    if item is None:
        raise AppError("NOT_FOUND", "事项不存在", 404, {"work_item_id": item_id})
    return item


def _ensure_refs(
    session: Session, course_id: str | None, project_id: str | None
) -> None:
    if course_id and session.get(Course, course_id) is None:
        raise AppError("NOT_FOUND", "课程不存在", 404, {"course_id": course_id})
    if project_id and session.get(Project, project_id) is None:
        raise AppError("NOT_FOUND", "项目不存在", 404, {"project_id": project_id})


def _normalize_datetimes(data: dict, tz: ZoneInfo) -> None:
    for field in DATETIME_FIELDS:
        if field in data and data[field] is not None:
            data[field] = as_utc(data[field], tz)


def serialize_item(
    item: WorkItem,
    tz: ZoneInfo,
    *,
    course_name: str | None = None,
    project_name: str | None = None,
) -> dict:
    session = object_session(item)
    if session is not None:
        course = session.get(Course, item.course_id) if item.course_id else None
        project = session.get(Project, item.project_id) if item.project_id else None
        course_name = course.name if course else None
        project_name = project.name if project else None
    else:
        if course_name is None and item.course is not None:
            course_name = item.course.name
        if project_name is None and item.project is not None:
            project_name = item.project.name
    return {
        "id": item.id,
        "title": item.title,
        "notes": item.notes,
        "item_type": item.item_type,
        "source_type": item.source_type,
        "status": item.status,
        "priority": item.priority,
        "due_at": iso(item.due_at, tz),
        "planned_start_at": iso(item.planned_start_at, tz),
        "planned_end_at": iso(item.planned_end_at, tz),
        "estimate_minutes": item.estimate_minutes,
        "blocked_reason": item.blocked_reason,
        "course_id": item.course_id,
        "course_name": course_name,
        "project_id": item.project_id,
        "project_name": project_name,
        "source_url": item.source_url,
        "external_id": item.external_id,
        "external_status": item.external_status,
        "needs_review": item.needs_review,
        "created_at": iso(item.created_at, tz),
        "updated_at": iso(item.updated_at, tz),
    }


def create_item(
    session: Session,
    payload: WorkItemCreate,
    *,
    project_id: str | None = None,
    source_type: str | None = None,
    item_type: str | None = None,
) -> WorkItem:
    tz = current_tz(session)
    data = payload.model_dump(exclude_unset=True)
    data.setdefault("title", payload.title)
    data["item_type"] = item_type or data.get("item_type") or "task"
    data["source_type"] = source_type or "manual"
    if project_id:
        data["project_id"] = project_id
    _normalize_datetimes(data, tz)
    _ensure_refs(session, data.get("course_id"), data.get("project_id"))

    status = data.get("status", "inbox")
    blocked_reason = data.get("blocked_reason")

    item = WorkItem(
        title=data["title"],
        notes=data.get("notes"),
        item_type=data["item_type"],
        source_type=data["source_type"],
        status=status,
        priority=data.get("priority", "normal"),
        due_at=data.get("due_at"),
        planned_start_at=data.get("planned_start_at"),
        planned_end_at=data.get("planned_end_at"),
        estimate_minutes=data.get("estimate_minutes"),
        blocked_reason=blocked_reason,
        course_id=data.get("course_id"),
        project_id=data.get("project_id"),
    )
    if status == "done":
        item.completed_at = utcnow()
    session.add(item)
    session.flush()
    return item


def _validate_transition(current: str, target: str) -> None:
    if current == "dismissed" and target != "dismissed":
        raise AppError(
            "WORK_ITEM_INVALID_TRANSITION",
            "已忽略的事项不能重新激活",
            409,
            {"from": current, "to": target},
        )


def update_item(session: Session, item: WorkItem, payload: WorkItemUpdate) -> WorkItem:
    tz = current_tz(session)
    data = payload.model_dump(exclude_unset=True)
    for field in REQUIRED_FIELDS:
        if field in data and data[field] is None:
            raise AppError(
                "VALIDATION_ERROR", f"{field} 不能为空", 422, {"field": field}
            )
    _normalize_datetimes(data, tz)
    _ensure_refs(
        session,
        data.get("course_id", item.course_id),
        data.get("project_id", item.project_id),
    )

    if "status" in data and data["status"] != item.status:
        target = data["status"]
        _validate_transition(item.status, target)
        if target == "done":
            item.completed_at = item.completed_at or utcnow()
        elif item.status == "done":
            item.completed_at = None

    for field in (
        "title",
        "notes",
        "item_type",
        "priority",
        "status",
        "due_at",
        "planned_start_at",
        "planned_end_at",
        "estimate_minutes",
        "blocked_reason",
        "course_id",
        "project_id",
    ):
        if field in data:
            setattr(item, field, data[field])

    session.flush()
    return item


def list_items(
    session: Session,
    *,
    status: str | None = None,
    source_type: str | None = None,
    project_id: str | None = None,
    course_id: str | None = None,
    q: str | None = None,
    limit: int = 100,
) -> Sequence[WorkItem]:
    statement = select(WorkItem)
    if status:
        statement = statement.where(WorkItem.status == status)
    if source_type:
        statement = statement.where(WorkItem.source_type == source_type)
    if project_id:
        statement = statement.where(WorkItem.project_id == project_id)
    if course_id:
        statement = statement.where(WorkItem.course_id == course_id)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            WorkItem.title.ilike(pattern) | WorkItem.notes.ilike(pattern)
        )
    statement = statement.order_by(WorkItem.created_at, WorkItem.id).limit(limit)
    return session.scalars(statement).unique().all()


def delete_item(session: Session, item: WorkItem) -> None:
    session.delete(item)
    session.flush()


def open_count(session: Session, *, course_id: str | None = None,
               project_id: str | None = None) -> int:
    statement = select(WorkItem).where(WorkItem.status.in_(ACTIVE_STATUSES))
    if course_id:
        statement = statement.where(WorkItem.course_id == course_id)
    if project_id:
        statement = statement.where(WorkItem.project_id == project_id)
    return len(session.scalars(statement).unique().all())
