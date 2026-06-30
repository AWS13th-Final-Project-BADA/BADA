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

    try:
        from aws_xray_sdk.core import xray_recorder, patch_all

        xray_recorder.configure(
            service="bada-worker",
            sampling=True,
            context_missing="IGNORE_ERROR",  # 세그먼트 없어도 에러 안 뱉음
        )

        patch_all()
    except Exception:
        pass  # X-Ray 초기화 실패해도 Worker 정상 동작
