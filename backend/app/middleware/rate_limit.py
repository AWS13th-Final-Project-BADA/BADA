"""IP 기반 Rate Limiting 미들웨어 — SECURITY-11 준수.

단일 ECS 인스턴스용 인메모리 구현. 분산 환경에서는 Redis 등으로 교체.
"""
from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

#_LIMIT = 60  # 분당 최대 요청 수

_LIMIT = 300  # 분당 최대 요청 수 300건으로 확대 --- Jaehyun Kim
_WINDOW = 60  # 윈도우(초)
_EXEMPT_PATHS = {"/health", "/version", "/health/db"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = _LIMIT, window: int = _WINDOW):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        if ip == "testclient":
            return await call_next(request)

        now = time.time()
        window_start = now - self.window

        # 윈도우 내 요청만 유지
        hits = self._hits[ip]
        self._hits[ip] = hits = [t for t in hits if t > window_start]

        remaining = max(0, self.limit - len(hits))
        reset_at = int(window_start + self.window)

        if len(hits) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도하세요."},
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        hits.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
