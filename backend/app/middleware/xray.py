"""AWS X-Ray 미들웨어 — 분산 추적 (API → SQS → Worker 전체 Service Map).

환경변수 XRAY_ENABLED=true 일 때만 활성화. 로컬에서는 비활성.
ECS Task Role에 xray:PutTraceSegments + xray:PutTelemetryRecords 권한 필요.

X-Ray SDK는 FastAPI 전용 미들웨어를 제공하지 않으므로,
Starlette(ASGI) 기반 미들웨어로 세그먼트를 수동 생성한다.
"""
from __future__ import annotations

import os

XRAY_ENABLED = os.environ.get("XRAY_ENABLED", "false").lower() == "true"


def setup_xray(app):
    """FastAPI 앱에 X-Ray 추적 적용. XRAY_ENABLED=false면 no-op."""
    if not XRAY_ENABLED:
        return

    from aws_xray_sdk.core import xray_recorder, patch_all
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response

    xray_recorder.configure(
        service="bada-backend",
        sampling=True,
        context_missing="LOG_ERROR",
    )

    # boto3, requests, sqlalchemy 자동 패치 → 하위 호출도 추적
    patch_all()

    class XRayMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            # health check는 트레이싱 스킵 (ALB unhealthy 방지)
            if request.url.path in ("/health", "/health/db", "/version", "/metrics"):
                return await call_next(request)

            segment = xray_recorder.begin_segment(name="bada-backend")
            segment.put_http_meta("url", str(request.url))
            segment.put_http_meta("method", request.method)
            segment.put_http_meta("user_agent", request.headers.get("user-agent", ""))
            try:
                response = await call_next(request)
                segment.put_http_meta("status", response.status_code)
                return response
            except Exception as e:
                segment.add_exception(e)
                raise
            finally:
                xray_recorder.end_segment()

    app.add_middleware(XRayMiddleware)
