"""Worker 전사 서비스 — process_transcription 오케스트레이션 및 포맷팅.

오디오 Evidence에 대해 Transcribe 잡을 시작하고, 5초 간격 폴링(최대 10분)으로
완료를 대기한 뒤, 화자 분리 결과를 포맷팅하여 반환한다.
Worker는 결과를 반환하고, DB 기록은 호출자(Backend)가 담당한다.
"""
from __future__ import annotations

import logging
import time

from providers.transcribe import TranscriptionResult, get_transcriber

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_LANGUAGE_CODE = "ko-KR"
_POLL_INTERVAL_SECONDS = 5
_TIMEOUT_SECONDS = 600  # 10분


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_diarized_text(result: TranscriptionResult) -> str:
    """화자별 세그먼트를 'Speaker N: text' 형식으로 결합.

    각 세그먼트는 줄바꿈으로 구분된다. 빈 segments일 경우 빈 문자열을 반환한다.

    Args:
        result: TranscriptionResult (화자 분리 세그먼트 목록)

    Returns:
        포맷팅된 전사 텍스트 문자열
    """
    if not result.segments:
        return ""

    lines = [f"{seg.speaker_label}: {seg.text}" for seg in result.segments]
    return "\n".join(lines)


def process_transcription(
    s3_uri: str,
    language_code: str | None = None,
    job_name: str | None = None,
) -> dict:
    """전사 전체 흐름 오케스트레이션.

    1. Transcriber 프로바이더 획득
    2. 전사 잡 시작 (job_name은 호출자가 생성하여 전달)
    3. 5초 간격 폴링 (최대 10분 타임아웃)
    4. 성공 시 화자 분리 텍스트 포맷팅
    5. 결과 dict 반환 (DB 기록은 호출자 담당)

    Args:
        s3_uri: S3에 저장된 오디오 파일 URI (s3://bucket/key)
        language_code: Amazon Transcribe 언어 코드. None이면 "ko-KR" 사용.
        job_name: 전사 잡 고유 이름. None이면 타임스탬프 기반으로 자동 생성.
            호출자가 네이밍 컨벤션 `bada-{case_id[:8]}-{evidence_id[:8]}-{timestamp}`
            형식으로 생성하여 전달하는 것을 권장한다.

    Returns:
        {
            "status": "done" | "failed",
            "text": str | None,   # 성공 시 포맷팅된 전사 텍스트
            "error": str | None,  # 실패 시 에러 사유
        }
    """
    lang = language_code or _DEFAULT_LANGUAGE_CODE

    # job_name 자동 생성 (호출자가 전달하지 않은 경우)
    if not job_name:
        job_name = f"bada-transcribe-{int(time.time())}"

    transcriber = get_transcriber()

    # 1. 잡 시작
    try:
        transcriber.start_job(s3_uri=s3_uri, language_code=lang, job_name=job_name)
        logger.info("Transcription job started: %s (lang=%s)", job_name, lang)
    except Exception as exc:
        logger.error("Failed to start transcription job %s: %s", job_name, exc)
        return {"status": "failed", "text": None, "error": f"job_start_error: {exc}"}

    # 2. 폴링 (5초 간격, 최대 10분)
    elapsed = 0
    while elapsed < _TIMEOUT_SECONDS:
        time.sleep(_POLL_INTERVAL_SECONDS)
        elapsed += _POLL_INTERVAL_SECONDS

        try:
            status = transcriber.get_job_status(job_name)
        except Exception as exc:
            logger.error("Failed to poll job status %s: %s", job_name, exc)
            return {"status": "failed", "text": None, "error": f"poll_error: {exc}"}

        if status.status == "COMPLETED":
            # 3. 결과 가져오기
            try:
                result = transcriber.get_result(job_name)
            except Exception as exc:
                logger.error("Failed to get result for %s: %s", job_name, exc)
                return {"status": "failed", "text": None, "error": f"result_fetch_error: {exc}"}

            # 4. 포맷팅
            text = format_diarized_text(result)
            logger.info("Transcription completed: %s (%d segments)", job_name, len(result.segments))
            return {"status": "done", "text": text, "error": None}

        if status.status == "FAILED":
            reason = status.failure_reason or "unknown"
            logger.error("Transcription job failed: %s reason=%s", job_name, reason)
            return {"status": "failed", "text": None, "error": reason}

        # IN_PROGRESS 또는 QUEUED → 계속 폴링
        logger.debug("Job %s status: %s (elapsed %ds)", job_name, status.status, elapsed)

    # 타임아웃
    logger.error("Transcription job timed out: %s (elapsed %ds)", job_name, elapsed)
    return {"status": "failed", "text": None, "error": "timeout"}
