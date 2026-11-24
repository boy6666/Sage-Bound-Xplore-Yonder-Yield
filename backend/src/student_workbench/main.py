from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, models  # noqa: F401  (registers ORM metadata)
from .api import connections, courses, dashboard, projects, system, work_items
from .config import AppConfig
from .db import Base, create_db_engine, create_session_factory, session_middleware
from .errors import (
    AppError,
    app_error_handler,
    http_error_handler,
    validation_error_handler,
)
from .migrations import ensure_schema
from .security import origin_guard
from .services.settings import get_settings_row


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or AppConfig.from_env()
    config.ensure_data_dir()
    config.apply_runtime_env()

    engine = create_db_engine(config.resolved_db_url)
    Base.metadata.create_all(engine)
    ensure_schema(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        get_settings_row(session)
        session.commit()

    app = FastAPI(title="Student Workbench", version=__version__)
    app.state.config = config
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)

    app.middleware("http")(session_middleware)
    app.middleware("http")(origin_guard)

    app.include_router(system.router)
    app.include_router(work_items.router)
    app.include_router(projects.router)
    app.include_router(projects.milestones_router)
    app.include_router(courses.router)
    app.include_router(courses.identities_router)
    app.include_router(connections.router)
    app.include_router(connections.sync_router)
    app.include_router(dashboard.router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
