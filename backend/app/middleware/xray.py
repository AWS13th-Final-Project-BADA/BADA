"""AWS X-Ray 미들웨어 — 분산 추적 (API → SQS → Worker 전체 Service Map).

환경변수 XRAY_ENABLED=true 일 때만 활성화. 로컬에서는 비활성.
ECS Task Role에 xray:PutTraceSegments + xray:PutTelemetryRecords 권한 필요.

안전 설계:
- patch_all() 사용 안 함 (기존 boto3/SQS/S3 호출 방해 방지)
- 수동 세그먼트만 생성 (Service Map에 노드 표시 목적)
- context_missing="IGNORE_ERROR" (daemon 없어도 에러 안 뱉음)
- health check 경로 스킵 (ALB unhealthy 방지)
"""
from __future__ import annotations

import os

XRAY_ENABLED = os.environ.get("XRAY_ENABLED", "false").lower() == "true"


def setup_xray(app):
    """FastAPI 앱에 X-Ray 추적 적용. XRAY_ENABLED=false면 no-op."""
    if not XRAY_ENABLED:
        return

    try:
        from aws_xray_sdk.core import xray_recorder
        from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
        from starlette.requests import Request
        from starlette.responses import Response

        xray_recorder.configure(
            service="bada-backend",
            sampling=True,
            context_missing="IGNORE_ERROR",
        )

        # patch_all() 의도적으로 사용하지 않음 — 기존 비즈니스 로직 방해 방지

        class XRayMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
                # health check / metrics는 트레이싱 스킵
                if request.url.path in ("/health", "/health/db", "/version", "/metrics"):
                    return await call_next(request)

                segment = None
                try:
                    segment = xray_recorder.begin_segment(name="bada-backend")
                    segment.put_http_meta("url", str(request.url))
                    segment.put_http_meta("method", request.method)
                except Exception:
                    # X-Ray 세그먼트 생성 실패해도 요청 처리는 계속
                    pass

                try:
                    response = await call_next(request)
                    if segment:
                        segment.put_http_meta("status", response.status_code)
                    return response
                except Exception as e:
                    if segment:
                        segment.add_exception(e)
                    raise
                finally:
                    try:
                        if segment:
                            xray_recorder.end_segment()
                    except Exception:
                        pass

        app.add_middleware(XRayMiddleware)

    except ImportError:
        pass  # aws_xray_sdk 미설치 환경 (로컬)
