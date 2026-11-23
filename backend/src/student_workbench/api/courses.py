from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import (
    CourseCreate,
    CourseDetailOut,
    CourseIdentityOut,
    CourseListOut,
    CourseOut,
    CreateCourseFromIdentity,
    IdentityLink,
    ScheduleOut,
    UnmatchedListOut,
)
from ..services.courses import (
    course_detail,
    create_course,
    create_course_from_identity,
    get_course,
    get_identity,
    link_identity,
    list_courses,
    schedule_payload,
    serialize_course,
    serialize_identity,
    unlink_identity,
    unmatched_identities,
)
from ..services.settings import current_tz

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])
identities_router = APIRouter(prefix="/api/v1/course-identities", tags=["courses"])


@router.get("", response_model=CourseListOut)
def get_courses(session: Session = Depends(get_session)):
    tz = current_tz(session)
    return {"items": list_courses(session, tz)}


@router.post("", response_model=CourseOut, status_code=201)
def create_course_endpoint(
    payload: CourseCreate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    return serialize_course(session, create_course(session, payload), tz)


@router.get("/schedule", response_model=ScheduleOut)
def get_schedule(
    week: int | None = Query(default=None, ge=1, le=60),
    session: Session = Depends(get_session),
):
    tz = current_tz(session)
    return schedule_payload(session, tz, week)


@router.get("/{course_id}", response_model=CourseDetailOut)
def get_course_detail(course_id: str, session: Session = Depends(get_session)):
    tz = current_tz(session)
    return course_detail(session, get_course(session, course_id), tz)


@identities_router.get("/unmatched", response_model=UnmatchedListOut)
def get_unmatched(session: Session = Depends(get_session)):
    return {"items": unmatched_identities(session)}


@identities_router.post("/{identity_id}/link", response_model=CourseIdentityOut)
def link_course_identity(
    identity_id: str, payload: IdentityLink, session: Session = Depends(get_session)
):
    identity = link_identity(session, get_identity(session, identity_id), payload.course_id)
    return serialize_identity(identity)


@identities_router.post("/{identity_id}/unlink", response_model=CourseIdentityOut)
def unlink_course_identity(identity_id: str, session: Session = Depends(get_session)):
    identity = unlink_identity(session, get_identity(session, identity_id))
    return serialize_identity(identity)


@identities_router.post(
    "/{identity_id}/create-course", response_model=CourseOut, status_code=201
)
def create_course_for_identity(
    identity_id: str,
    payload: CreateCourseFromIdentity,
    session: Session = Depends(get_session),
):
    tz = current_tz(session)
    identity = get_identity(session, identity_id)
    course = create_course_from_identity(session, identity, payload.name)
    return serialize_course(session, course, tz)
