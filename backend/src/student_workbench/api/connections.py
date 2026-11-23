from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Connection
from ..schemas import (
    ChallengeRequest,
    ConnectionCreate,
    ConnectionListOut,
    ConnectionOut,
    LoginRequest,
    LoginResult,
    SyncRunListOut,
    SyncRunOut,
    SyncStartOut,
)
from ..services.connections import (
    delete_connection,
    get_connection,
    list_connections,
    serialize_connection,
    start_login,
    submit_challenge,
)
from ..services.settings import current_tz
from ..services.sync.executor import get_run, list_runs, serialize_run, start_sync

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])
sync_router = APIRouter(prefix="/api/v1/sync-runs", tags=["sync"])


@router.get("", response_model=ConnectionListOut)
def get_connections(session: Session = Depends(get_session)):
    tz = current_tz(session)
    return {"items": list_connections(session, tz)}


@router.post("", response_model=ConnectionOut, status_code=201)
def create_connection_endpoint(
    payload: ConnectionCreate, session: Session = Depends(get_session)
):
    tz = current_tz(session)
    connection = Connection(
        kind=payload.kind,
        provider=payload.provider,
        display_name=payload.display_name,
        status="unconfigured",
    )
    session.add(connection)
    session.flush()
    return serialize_connection(connection, tz)


@router.post(
    "/{connection_id}/login",
    response_model=LoginResult,
    response_model_exclude_none=True,
)
def login(
    connection_id: str, payload: LoginRequest, session: Session = Depends(get_session)
):
    connection = get_connection(session, connection_id)
    return start_login(
        session,
        connection,
        username=payload.username,
        password=payload.password,
        save_password=payload.save_password,
    )


@router.post(
    "/{connection_id}/login/challenge",
    response_model=LoginResult,
    response_model_exclude_none=True,
)
def login_challenge(
    connection_id: str, payload: ChallengeRequest, session: Session = Depends(get_session)
):
    connection = get_connection(session, connection_id)
    return submit_challenge(
        session, connection, challenge_id=payload.challenge_id, code=payload.code
    )


@router.post("/{connection_id}/sync", response_model=SyncStartOut, status_code=202)
def sync_connection(connection_id: str, session: Session = Depends(get_session)):
    connection = get_connection(session, connection_id)
    run = start_sync(session, connection)
    return {"sync_run_id": run.id}


@router.delete("/{connection_id}", status_code=204)
def remove_connection(connection_id: str, session: Session = Depends(get_session)):
    delete_connection(session, get_connection(session, connection_id))
    return Response(status_code=204)


@sync_router.get("", response_model=SyncRunListOut)
def get_sync_runs(
    limit: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
):
    tz = current_tz(session)
    runs = list_runs(session, limit=limit)
    return {"items": [serialize_run(session, run, tz) for run in runs]}


@sync_router.get("/{run_id}", response_model=SyncRunOut)
def get_sync_run(run_id: str, session: Session = Depends(get_session)):
    tz = current_tz(session)
    return serialize_run(session, get_run(session, run_id), tz)
