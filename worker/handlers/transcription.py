"""전사 handler — transcribe 메시지 처리 (2단계: DB 직접 저장).

메시지 형식:
    {"task": "transcribe", "evidence_id": "...", "case_id": "...",
     "s3_key": "cases/.../audio.mp3", "language_code": "ko-KR"}

흐름:
    1. s3_key → s3_uri 변환
    2. services.transcription.process_transcription() 호출
    3. 결과를 DB Evidence에 직접 저장
    4. 실패 시 예외 → consumer가 재시도/DLQ 처리

멱등성: ocr_text/ocr_status를 덮어쓰므로 중복 수신에 안전.
"""
from __future__ import annotations

import logging
import os
import time

from db import get_session
from services.transcription import process_transcription

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "")


def handle(message: dict) -> None:
    """transcribe 메시지 처리. 실패 시 예외 → consumer 재시도/DLQ."""
    evidence_id = message.get("evidence_id")
    case_id = message.get("case_id", "")
    s3_key = message.get("s3_key")
    language_code = message.get("language_code", "ko-KR")

    if not (evidence_id and s3_key):
        raise ValueError("transcribe: 'evidence_id' and 's3_key' are required")

    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET 환경변수가 설정되지 않았습니다")

    s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
    job_name = f"bada-{case_id[:8]}-{evidence_id[:8]}-{int(time.time())}"

    logger.info("transcribe 시작: evidence_id=%s, s3_uri=%s", evidence_id, s3_uri)

    result = process_transcription(s3_uri, language_code, job_name=job_name)

    # DB 저장
    session = get_session()
    try:
        _save_result(session, evidence_id, result)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if result["status"] == "failed":
        raise RuntimeError(f"transcription failed: {result['error']}")

    logger.info("transcribe 완료: evidence_id=%s", evidence_id)


def _save_result(session, evidence_id: str, result: dict) -> None:
    import sys
    from pathlib import Path
    _BACKEND = Path(__file__).resolve().parents[2] / "backend"
    if str(_BACKEND) not in sys.path:
        sys.path.insert(0, str(_BACKEND))

    from app.models import Evidence

    ev = session.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        logger.warning("Evidence not found: %s (이미 삭제됨?)", evidence_id)
        return

    if result["status"] == "done":
        ev.ocr_text = result["text"]
        ev.ocr_status = "done"
    else:
        ev.ocr_status = "failed"

    session.commit()
