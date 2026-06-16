"""Worker 전사 서비스 — process_transcription 오케스트레이션 및 포맷팅.

오디오 Evidence에 대해 Transcribe 잡을 시작하고, 5초 간격 폴링(최대 10분)으로
완료를 대기한 뒤, 화자 분리 결과를 포맷팅하여 반환한다.
Worker는 결과를 반환하고, DB 기록은 호출자(Backend)가 담당한다.

후처리: Transcribe 원문을 Bedrock Claude로 보정하여 오인식/누락을 복원한다.
"""
from __future__ import annotations

import json
import logging
import time

from config import PROVIDER_MODE
from providers.transcribe import TranscriptionResult, get_transcriber

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_LANGUAGE_CODE = "ko-KR"
_POLL_INTERVAL_SECONDS = 5
_TIMEOUT_SECONDS = 600  # 10분

# Claude 보정 프롬프트 (전화 통화 전사 후처리)
_REFINE_SYSTEM = (
    "당신은 한국어 전화 통화 전사본을 교정하는 도우미입니다. "
    "임금체불 상담 맥락에서 음성 인식 오류를 교정하고, "
    "문맥상 빠진 조사·어미를 복원하세요. "
    "단, 없는 내용을 지어내지 마세요. 원래 말한 내용만 복원합니다."
)

_REFINE_PROMPT = """아래는 전화 통화 음성인식(STT) 결과입니다. 임금체불 상담 맥락입니다.

[전사 원문]
{transcript}

다음을 교정하세요:
1. 음성인식 오타 교정 (예: "원금" → "월급", "시급" 문맥에 맞게)
2. 도메인 용어 교정: 월급, 시급, 공제, 기숙사비, 야근, 잔업, 수당, 계약서, 명세서, 급여, 입금
3. 빠진 조사/어미 복원 (자연스러운 한국어로)
4. 화자 라벨(Speaker 0:, Speaker 1:) 형식은 그대로 유지

절대 없는 내용을 추가하지 마세요. 원문에 있는 발화만 교정합니다.
교정된 전체 텍스트만 출력하세요 (설명 없이)."""


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


def refine_transcript(raw_text: str) -> str:
    """Transcribe 원문을 Bedrock Claude로 보정한다.

    전화 통화 음성인식에서 흔한 오인식(도메인 용어 오류, 조사 누락)을 교정.
    실패 시 원문 그대로 반환 (graceful degradation).
    PROVIDER_MODE=local이면 보정 건너뜀.
    """
    if PROVIDER_MODE != "aws":
        return raw_text

    if not raw_text or len(raw_text.strip()) < 10:
        return raw_text

    try:
        from providers._bedrock import invoke, text_block
        prompt = _REFINE_PROMPT.format(transcript=raw_text)
        blocks = [text_block(prompt)]
        refined = invoke(_REFINE_SYSTEM, blocks, max_tokens=4000)
        # 기본 검증: 보정 결과가 원문보다 극단적으로 짧으면(50% 미만) 원문 유지
        if refined and len(refined.strip()) >= len(raw_text.strip()) * 0.5:
            return refined.strip()
        logger.warning("Refined text too short, keeping original")
        return raw_text
    except Exception as e:
        logger.warning("Transcript refinement failed, keeping original: %s", e)
        return raw_text


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

            # 5. Claude 보정 (전화 통화 오인식 교정)
            text = refine_transcript(text)

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
