"""증거 수집 에이전트 브릿지 — worker.services.evidence_intake 호출.

스캔(분류만, 싸다) / 정밀(분류+OCR+키워드, 비싸다) 두 경로를 노출한다.
최종 등록은 사용자 승인 후 기존 /upload → /extract 로 진행(HITL, OCR 1회).
"""
from __future__ import annotations

import sys
from pathlib import Path

# 모노레포 worker 패키지 임포트 경로 (analysis_service와 동일 패턴)
_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))


def scan_images(images: list[tuple[str, bytes]]) -> dict:
    """[스캔] 여러 이미지를 분류만으로 빠르게 훑어 등급별 후보로 묶는다(OCR X)."""
    from services.evidence_intake import assess_batch
    return assess_batch(images)


def assess_one_deep(image_bytes: bytes) -> dict:
    """[정밀] 1장을 분류+OCR+키워드 교차검증으로 확인(정확성 3종)."""
    from services.evidence_intake import assess_deep
    return assess_deep(image_bytes)
