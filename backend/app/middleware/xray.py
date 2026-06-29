"""AWS X-Ray 미들웨어 — 분산 추적 (API → SQS → Worker 전체 Service Map).

환경변수 XRAY_ENABLED=true 일 때만 활성화. 로컬에서는 비활성.
ECS Task Role에 xray:PutTraceSegments + xray:PutTelemetryRecords 권한 필요.
"""
from __future__ import annotations

import os

XRAY_ENABLED = os.environ.get("XRAY_ENABLED", "false").lower() == "true"


def setup_xray(app):
    """FastAPI 앱에 X-Ray 미들웨어 적용. XRAY_ENABLED=false면 no-op."""
    if not XRAY_ENABLED:
        return

    from aws_xray_sdk.core import xray_recorder, patch_all
    from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

    xray_recorder.configure(
        service="bada-backend",
        sampling=True,
        context_missing="LOG_ERROR",
        daemon_address="127.0.0.1:2000",
    )

    # boto3, requests, sqlalchemy 자동 패치 → 하위 호출도 추적
    patch_all()

    XRayMiddleware(app, xray_recorder)
