"""Request ID 미들웨어 — 각 요청에 고유 ID 부여 + 응답 헤더에 포함.

request_id는 logging_config의 ContextVar에 저장되어 모든 로그에 자동 포함.
"""
from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ..logging_config import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 클라이언트가 보낸 X-Request-ID가 있으면 사용, 없으면 생성
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(rid)

        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
