"""Prometheus 메트릭 미들웨어 + /metrics 엔드포인트."""
from __future__ import annotations

import time

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
ANALYSIS_RUNS = Counter(
    "analysis_runs_total",
    "Total analysis runs",
    ["status"],
)
OCR_REQUESTS = Counter(
    "ocr_requests_total",
    "Total OCR requests",
    ["provider", "status"],
)


def _normalize_path(path: str) -> str:
    """UUID 등 동적 세그먼트를 일반화하여 카디널리티 폭발 방지."""
    parts = path.strip("/").split("/")
    normalized = []
    for p in parts:
        if len(p) == 36 and "-" in p:  # UUID
            normalized.append("{id}")
        else:
            normalized.append(p)
    return "/" + "/".join(normalized)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

        method = request.method
        path = _normalize_path(request.url.path)
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        status = str(response.status_code)

        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        REQUEST_DURATION.labels(method=method, path=path).observe(duration)

        return response
