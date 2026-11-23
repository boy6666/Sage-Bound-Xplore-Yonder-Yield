from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from starlette.responses import Response


class Base(DeclarativeBase):
    pass


def create_db_engine(db_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(db_url, connect_args=connect_args)

    if db_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _record):  # pragma: no cover - driver hook
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=True)


def get_session(request: Request) -> Session:
    """Return the request-scoped session created by ``session_middleware``."""
    session = getattr(request.state, "db_session", None)
    if session is None:  # pragma: no cover - defensive, only when middleware is bypassed
        session = request.app.state.session_factory()
        request.state.db_session = session
    return session


async def session_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Commit before the response is sent so a write is visible to the next request.

    A yield-based FastAPI dependency commits only after the response has been sent,
    which lets a client that immediately re-reads hit SQLite before the transaction
    is durable (observed as a spurious 404 right after a 201).
    """
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:  # pragma: no cover - app always sets it
        return await call_next(request)

    session: Session = factory()
    request.state.db_session = session
    try:
        response = await call_next(request)
        if response.status_code < 400:
            session.commit()
        else:
            session.rollback()
        return response
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
