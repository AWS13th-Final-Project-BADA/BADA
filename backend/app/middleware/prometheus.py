"""Prometheus 메트릭 미들웨어 + /metrics 엔드포인트."""
from __future__ import annotations

import time

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ── 인프라 메트릭 ──
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

# ── 비즈니스 메트릭 ──
CASES_CREATED = Counter(
    "bada_cases_created_total",
    "Total cases created",
)
EVIDENCES_UPLOADED = Counter(
    "bada_evidences_uploaded_total",
    "Total evidence files uploaded",
    ["category"],
)
ANALYSIS_RUNS = Counter(
    "bada_analysis_runs_total",
    "Total analysis pipeline runs",
    ["status"],
)
ANALYSIS_DURATION = Histogram(
    "bada_analysis_duration_seconds",
    "Analysis pipeline duration",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)
PDF_GENERATED = Counter(
    "bada_pdf_generated_total",
    "Total PDF Evidence Packs generated",
)
BEDROCK_CALLS = Counter(
    "bada_bedrock_calls_total",
    "Total Bedrock LLM calls",
    ["model", "status"],
)
BEDROCK_LATENCY = Histogram(
    "bada_bedrock_latency_seconds",
    "Bedrock call latency",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
)
SQS_MESSAGES_PROCESSED = Counter(
    "bada_sqs_messages_processed_total",
    "Total SQS messages processed by worker",
    ["action", "status"],
)


def _normalize_path(path: str) -> str:
    """UUID 등 동적 세그먼트를 일반화하여 카디널리티 폭발 방지."""
    parts = path.strip("/").split("/")
    normalized = []
    for p in parts:
        if len(p) == 36 and "-" in p:
            normalized.append("{id}")
        elif p.isdigit():
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
