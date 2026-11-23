"""ASGI entrypoint: `uvicorn student_workbench.asgi:app`."""

from __future__ import annotations

from .main import create_app

app = create_app()
