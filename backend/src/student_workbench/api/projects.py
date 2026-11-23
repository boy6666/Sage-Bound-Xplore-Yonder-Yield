from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Project
from ..schemas import (
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
    ProjectCreate,
    ProjectDetailOut,
    ProjectListOut,
    ProjectOut,
    ProjectUpdate,
    ScanOut,
    WorkItemCreate,
    WorkItemOut,
)
from ..services.projects import (
    create_milestone,
    create_project,
    delete_project,
    get_milestone,
    get_project,
    project_detail,
    scan_project,
    serialize_milestone,
    serialize_project,
    update_milestone,
    update_project,
)
from ..services.settings import current_tz
from ..services.work_items import create_item, serialize_item

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
milestones_router = APIRouter(prefix="/api/v1/milestones", tags=["projects"])


@router.get("", response_model=ProjectListOut)
def list_projects(
    status: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    tz = current_tz(session)
    statement = select(Project).order_by(Project.created_at, Project.id)
    if status:
        statement = statement.where(Project.status == status)
    projects = session.scalars(statement).all()
    return {"items": [serialize_project(session, project, tz) for project in projects]}


@router.post("", response_model=ProjectOut, status_code=201)
def create_project_endpoint(
    payload: ProjectCreate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    return serialize_project(session, create_project(session, payload), tz)


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project_detail(project_id: str, session: Session = Depends(get_session)):
    tz = current_tz(session)
    project = get_project(session, project_id)
    return project_detail(session, project, tz)


@router.patch("/{project_id}", response_model=ProjectOut)
def patch_project(
    project_id: str, payload: ProjectUpdate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    project = update_project(session, get_project(session, project_id), payload)
    return serialize_project(session, project, tz)


@router.delete("/{project_id}", status_code=204)
def remove_project(project_id: str, session: Session = Depends(get_session)):
    delete_project(session, get_project(session, project_id))
    return Response(status_code=204)


@router.post("/{project_id}/milestones", response_model=MilestoneOut, status_code=201)
def add_milestone(
    project_id: str, payload: MilestoneCreate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    milestone = create_milestone(session, project_id, payload)
    return serialize_milestone(milestone, tz)


@router.post("/{project_id}/todos", response_model=WorkItemOut, status_code=201)
def add_project_todo(
    project_id: str, payload: WorkItemCreate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    item = create_item(
        session,
        payload,
        project_id=project_id,
        source_type="project",
        item_type="task",
    )
    return serialize_item(item, tz)


@router.post("/{project_id}/scan", response_model=ScanOut)
def scan_project_endpoint(project_id: str, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    return scan_project(session, project)


@milestones_router.patch("/{milestone_id}", response_model=MilestoneOut)
def patch_milestone(
    milestone_id: str, payload: MilestoneUpdate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    milestone = update_milestone(session, get_milestone(session, milestone_id), payload)
    return serialize_milestone(milestone, tz)
