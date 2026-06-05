"""백그라운드 작업 실행 seam — '어떻게 돌릴지'를 한 곳에 가둔다(provider seam과 같은 패턴).

지금: 같은 프로세스의 ThreadPoolExecutor(인프라 불필요).
나중: 인프라(SQS/Celery 등)가 오면 submit_ocr 내부만 큐 enqueue로 교체.
      호출부(라우터)·데이터모델(ocr_status)·프론트(폴링)는 그대로.

원칙: 작업은 멱등(idempotent)해야 한다 — run_ocr_on_case는 'done'을 재처리하지 않으므로
      같은 작업이 두 번 실행돼도 안전(큐 재전송 대비).
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from ..db import SessionLocal

log = logging.getLogger("bada")

# 단일 서버 내 동시 OCR 수 제한(레이트리밋·메모리 보호). 인프라 전환 시 의미 없어짐.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr")


def submit_ocr(case_id: str) -> None:
    """사건의 OCR을 백그라운드로 실행. 즉시 반환(논블로킹)."""
    _executor.submit(_run_ocr, case_id)


def _run_ocr(case_id: str) -> None:
    # 백그라운드 스레드는 요청 세션을 못 쓴다 → 자체 세션 생성(check_same_thread=False).
    from .ocr_service import run_ocr_on_case
    db = SessionLocal()
    try:
        run_ocr_on_case(db, case_id)
    except Exception as e:  # 스레드에서 예외가 새지 않도록 흡수(상태는 failed로 기록됨)
        log.warning("background OCR failed for case %s: %s", case_id, e)
    finally:
        db.close()
