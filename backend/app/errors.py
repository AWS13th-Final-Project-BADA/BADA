"""공통 에러 처리 — 일관된 JSON 에러 응답. 모든 기능이 같은 포맷을 쓴다."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("bada")


def _body(code: str, message: str, detail=None):
    return {"error": {"code": code, "message": message, "detail": detail}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content=_body("http_error", str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422,
                            content=_body("validation_error", "요청 형식이 올바르지 않습니다.", exc.errors()))

    @app.exception_handler(NotImplementedError)
    async def _notimpl(request: Request, exc: NotImplementedError):
        # 아직 구현 안 된 AWS 모드 기능 등
        return JSONResponse(status_code=501,
                            content=_body("not_implemented", str(exc) or "아직 구현되지 않은 기능입니다."))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse(status_code=500,
                            content=_body("internal_error", "서버 내부 오류가 발생했습니다."))
