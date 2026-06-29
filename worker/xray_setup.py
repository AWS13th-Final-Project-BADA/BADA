"""Worker X-Ray 초기화 — SQS 메시지 처리 시 세그먼트 추적.

환경변수 XRAY_ENABLED=true 일 때만 활성화.
"""
from __future__ import annotations

import os

XRAY_ENABLED = os.environ.get("XRAY_ENABLED", "false").lower() == "true"


def init_xray():
    """Worker 프로세스 시작 시 X-Ray 초기화. 비활성이면 no-op."""
    if not XRAY_ENABLED:
        return

    from aws_xray_sdk.core import xray_recorder, patch_all

    xray_recorder.configure(
        service="bada-worker",
        sampling=True,
        context_missing="LOG_ERROR",
        daemon_address="127.0.0.1:2000",
    )

    # boto3(S3, SQS, Transcribe, Bedrock), requests(Upstage) 패치
    patch_all()
