"""백그라운드 작업 실행 seam — SQS를 통한 Worker 비동기 처리.

SQS 설정 시: Worker가 OCR을 별도 프로세스로 처리 (스케일 가능, 유실 없음).
SQS 미설정 시: ThreadPoolExecutor 폴백 (로컬 개발용).
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from ..config import settings
from ..db import SessionLocal

log = logging.getLogger("bada")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr")


def submit_ocr(case_id: str) -> None:
    """사건의 OCR을 비동기로 실행. SQS 설정 시 Worker로 전달, 아니면 로컬 스레드."""
    if settings.sqs_queue_url:
        import boto3
        client = boto3.client("sqs", region_name=settings.aws_region)
        client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps({"type": "extract_ocr", "case_id": case_id}),
        )
        return
    # 로컬 폴백
    _executor.submit(_run_ocr, case_id)


def _run_ocr(case_id: str) -> None:
    from .ocr_service import run_ocr_on_case
    db = SessionLocal()
    try:
        run_ocr_on_case(db, case_id)
    except Exception as e:
        log.warning("background OCR failed for case %s: %s", case_id, e)
    finally:
        db.close()
