"""전사 handler — transcribe 메시지 처리. (골격 — 음성인식 담당이 구현)

메시지 형식:
    {"task": "transcribe", "evidence_id": "...", "case_id": "...",
     "s3_key": "cases/.../audio.mp3", "language_code": "ko-KR"}

구현 가이드:
    1. s3_key → s3_uri 변환:  f"s3://{S3_BUCKET}/{s3_key}"
    2. services.transcription.process_transcription(s3_uri, language_code, job_name) 호출
         → {"status": "done"|"failed", "text": str|None, "error": str|None}
       (job_name 권장: f"bada-{case_id[:8]}-{evidence_id[:8]}-{int(time.time())}")
    3. 결과를 Evidence 에 저장:
         - 성공: Evidence.ocr_text = text, Evidence.ocr_status = "done"
         - 실패: Evidence.ocr_status = "failed"
       저장 방식은 분석 handler와 동일한 단계 전략을 따른다:
         · 1단계: 백엔드 엔드포인트 경유 (worker DB 불필요)
         · 2단계: worker가 DB(DATABASE_URL) 직접 저장
    4. 실패 시 예외를 올리면 consumer가 재시도/DLQ 처리한다.

환경변수:
    S3_BUCKET  오디오가 저장된 S3 버킷 (infra가 주입)
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "")


def handle(message: dict) -> None:
    evidence_id = message.get("evidence_id")
    s3_key = message.get("s3_key")
    if not (evidence_id and s3_key):
        raise ValueError("transcribe: 'evidence_id' and 's3_key' are required")

    # TODO(음성인식 담당): 위 구현 가이드 1~3 단계 구현.
    #   from services.transcription import process_transcription
    #   s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
    #   result = process_transcription(s3_uri, message.get("language_code"), job_name=...)
    #   ... Evidence.ocr_text / ocr_status 저장 ...
    raise NotImplementedError("transcribe handler 미구현 (담당: 음성인식)")
