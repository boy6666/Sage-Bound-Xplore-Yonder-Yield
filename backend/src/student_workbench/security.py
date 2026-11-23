from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

from .errors import error_body

WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
CLIENT_HEADER = "x-student-workbench-client"
LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme != "http":
        return False
    if parts.hostname not in LOCAL_HOSTS:
        return False
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        return False
    return True


async def origin_guard(request: Request, call_next):
    if request.method in WRITE_METHODS:
        client_header = request.headers.get(CLIENT_HEADER)
        origin = request.headers.get("origin")
        if client_header != "web" or not is_allowed_origin(origin):
            return JSONResponse(
                status_code=403,
                content=error_body("FORBIDDEN_ORIGIN", "写请求来源不合法"),
            )
    return await call_next(request)
