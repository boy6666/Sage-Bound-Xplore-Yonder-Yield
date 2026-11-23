from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.details),
    )


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    issues = []
    for error in exc.errors():
        issues.append(
            {
                "loc": [str(part) for part in error.get("loc", ())],
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
        )
    return JSONResponse(
        status_code=422,
        content=error_body("VALIDATION_ERROR", "请求体校验失败", {"issues": issues}),
    )


async def http_error_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if exc.status_code == 404:
        code = "NOT_FOUND"
        message = "资源不存在"
    elif exc.status_code == 405:
        code = "METHOD_NOT_ALLOWED"
        message = "方法不被允许"
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code, message),
        headers=getattr(exc, "headers", None),
    )
