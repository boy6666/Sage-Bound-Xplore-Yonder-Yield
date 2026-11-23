from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import WorkItemCreate, WorkItemListOut, WorkItemOut, WorkItemUpdate
from ..services.settings import current_tz
from ..services.work_items import (
    create_item,
    delete_item,
    get_item,
    list_items,
    serialize_item,
    update_item,
)

router = APIRouter(prefix="/api/v1/work-items", tags=["work-items"])


@router.get("", response_model=WorkItemListOut)
def list_work_items(
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    course_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    tz = current_tz(session)
    items = list_items(
        session,
        status=status,
        source_type=source_type,
        project_id=project_id,
        course_id=course_id,
        q=q,
        limit=limit,
    )
    return {"items": [serialize_item(item, tz) for item in items]}


@router.post("", response_model=WorkItemOut, status_code=201)
def create_work_item(
    payload: WorkItemCreate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    item = create_item(session, payload)
    return serialize_item(item, tz)


@router.get("/{item_id}", response_model=WorkItemOut)
def get_work_item(item_id: str, session: Session = Depends(get_session)):
    tz = current_tz(session)
    return serialize_item(get_item(session, item_id), tz)


@router.patch("/{item_id}", response_model=WorkItemOut)
def patch_work_item(
    item_id: str, payload: WorkItemUpdate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    item = update_item(session, get_item(session, item_id), payload)
    return serialize_item(item, tz)


@router.delete("/{item_id}", status_code=204)
def remove_work_item(item_id: str, session: Session = Depends(get_session)):
    delete_item(session, get_item(session, item_id))
    return Response(status_code=204)
