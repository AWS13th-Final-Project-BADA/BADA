"""Worker X-Ray 초기화 — SQS 메시지 처리 시 세그먼트 추적.

환경변수 XRAY_ENABLED=true 일 때만 활성화.

안전 설계:
- patch_all() 사용 안 함 (SQS/S3/Bedrock 호출 방해 방지)
- 수동 세그먼트만 생성 (Service Map에 Worker 노드 표시 목적)
- context_missing="IGNORE_ERROR" (daemon 없어도 에러 안 뱉음)
- 초기화 실패해도 Worker 정상 동작
"""
from __future__ import annotations

import os

XRAY_ENABLED = os.environ.get("XRAY_ENABLED", "false").lower() == "true"

_recorder = None


def init_xray():
    """Worker 프로세스 시작 시 X-Ray 초기화. 비활성이면 no-op."""
    global _recorder
    if not XRAY_ENABLED:
        return

    try:
        from aws_xray_sdk.core import xray_recorder

        xray_recorder.configure(
            service="bada-worker",
            sampling=True,
            context_missing="IGNORE_ERROR",
        )

        # patch_all() 의도적으로 사용하지 않음 — SQS/S3/Bedrock 호출 방해 방지
        _recorder = xray_recorder
    except Exception:
        pass  # X-Ray 초기화 실패해도 Worker 정상 동작


def begin_segment(name: str):
    """수동 세그먼트 시작. X-Ray 비활성이면 None 반환."""
    if not _recorder:
        return None
    try:
        return _recorder.begin_segment(name=name)
    except Exception:
        return None


def end_segment():
    """세그먼트 종료. 실패해도 무시."""
    if not _recorder:
        return
    try:
        _recorder.end_segment()
    except Exception:
        pass
