"""Transcribe provider — 음성 전사(Speech-to-Text).

담당: 오디오 파일을 텍스트로 변환한다.
AmazonTranscriber가 Amazon Transcribe API를 캡슐화하고,
화자 분리(Speaker Diarization)를 활성화하여 최대 5명의 화자를 구분한다.
PROVIDER_MODE에 따라 MockTranscriber(로컬) / AmazonTranscriber(AWS)로 분기한다.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from config import AWS_REGION, PROVIDER_MODE

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class TranscriptionStatus:
    """전사 잡의 현재 상태."""

    status: str  # "IN_PROGRESS" | "COMPLETED" | "FAILED"
    failure_reason: str | None = None


@dataclass
class SpeakerSegment:
    """화자별 발화 세그먼트."""

    speaker_label: str  # "Speaker 0", "Speaker 1", ...
    text: str


@dataclass
class TranscriptionResult:
    """전사 완료 결과. 화자 분리된 세그먼트 목록."""

    segments: list[SpeakerSegment] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------


class Transcriber(ABC):
    """전사 프로바이더 추상 인터페이스."""

    @abstractmethod
    def start_job(self, s3_uri: str, language_code: str, job_name: str) -> str:
        """전사 잡을 시작하고 job_name을 반환한다.

        Args:
            s3_uri: S3에 저장된 오디오 파일 URI (s3://bucket/key)
            language_code: Amazon Transcribe 언어 코드 (예: ko-KR)
            job_name: 고유 잡 이름

        Returns:
            제출된 job_name
        """
        ...

    @abstractmethod
    def get_job_status(self, job_name: str) -> TranscriptionStatus:
        """잡의 현재 상태를 반환한다.

        Args:
            job_name: 조회할 잡 이름

        Returns:
            TranscriptionStatus (status, failure_reason)
        """
        ...

    @abstractmethod
    def get_result(self, job_name: str) -> TranscriptionResult:
        """완료된 잡의 전사 결과를 반환한다.

        Args:
            job_name: 결과를 가져올 잡 이름

        Returns:
            TranscriptionResult (화자 분리 세그먼트 포함)
        """
        ...


# ---------------------------------------------------------------------------
# MockTranscriber — 로컬 개발용
# ---------------------------------------------------------------------------


class MockTranscriber(Transcriber):
    """로컬 개발용. 즉시 고정 텍스트 반환 (100ms 이내)."""

    def __init__(self) -> None:
        self._jobs: dict[str, str] = {}  # job_name → status

    def start_job(self, s3_uri: str, language_code: str, job_name: str) -> str:
        self._jobs[job_name] = "COMPLETED"
        return job_name

    def get_job_status(self, job_name: str) -> TranscriptionStatus:
        return TranscriptionStatus(status="COMPLETED")

    def get_result(self, job_name: str) -> TranscriptionResult:
        return TranscriptionResult(
            segments=[
                SpeakerSegment(speaker_label="Speaker 0", text="안녕하세요, 이번 달 급여가 아직 입금되지 않았습니다."),
                SpeakerSegment(speaker_label="Speaker 1", text="네, 확인해보겠습니다. 잠시만 기다려주세요."),
                SpeakerSegment(speaker_label="Speaker 0", text="지난달에도 같은 문제가 있었는데, 이번에도 늦어지는 건가요?"),
            ]
        )


# ---------------------------------------------------------------------------
# AmazonTranscriber — AWS 실제 연동
# ---------------------------------------------------------------------------


class AmazonTranscriber(Transcriber):
    """Amazon Transcribe API 래핑. 화자 분리 활성화 (최대 5명).

    boto3 클라이언트를 지연 임포트하여 로컬 환경에서 AWS 의존성 없이 모듈 로드 가능.
    """

    def __init__(self, region: str = "ap-northeast-2") -> None:
        import boto3  # 지연 임포트

        self._region = region
        self._client = boto3.client("transcribe", region_name=region)

    def start_job(self, s3_uri: str, language_code: str, job_name: str) -> str:
        """Amazon Transcribe에 전사 잡을 제출한다.

        전화 통화 최적화:
        - ChannelIdentification=True: 2채널(발신/수신) 분리 → 화자 구분 정확도 ↑
        - 채널 식별이 활성화되면 ShowSpeakerLabels와 동시 사용 불가 → 채널 우선
        - 채널 식별 실패(모노 파일 등) 시 화자 분리로 폴백
        """
        try:
            # 먼저 채널 식별 모드로 시도 (전화 통화 = 스테레오가 대부분)
            self._client.start_transcription_job(
                TranscriptionJobName=job_name,
                LanguageCode=language_code,
                Media={"MediaFileUri": s3_uri},
                Settings={
                    "ChannelIdentification": True,
                },
            )
        except Exception as e:
            # 채널 식별 실패(모노 파일 등) → 화자 분리로 폴백
            logger.info("Channel identification failed for %s, falling back to speaker diarization: %s", job_name, e)
            self._client.start_transcription_job(
                TranscriptionJobName=job_name + "-retry",
                LanguageCode=language_code,
                Media={"MediaFileUri": s3_uri},
                Settings={
                    "ShowSpeakerLabels": True,
                    "MaxSpeakerLabels": 5,
                },
            )
            return job_name + "-retry"
        return job_name

    def get_job_status(self, job_name: str) -> TranscriptionStatus:
        """Amazon Transcribe 잡 상태를 조회한다."""
        response = self._client.get_transcription_job(
            TranscriptionJobName=job_name,
        )
        job = response["TranscriptionJob"]
        status = job["TranscriptionJobStatus"]

        # Amazon Transcribe 상태: QUEUED, IN_PROGRESS, COMPLETED, FAILED
        failure_reason = None
        if status == "FAILED":
            failure_reason = job.get("FailureReason", "Unknown error")

        return TranscriptionStatus(status=status, failure_reason=failure_reason)

    def get_result(self, job_name: str) -> TranscriptionResult:
        """완료된 잡의 결과를 가져와 화자 분리 세그먼트로 파싱한다."""
        import json
        import urllib.request

        try:
            response = self._client.get_transcription_job(
                TranscriptionJobName=job_name,
            )
            job = (response or {}).get("TranscriptionJob") or {}
            transcript = job.get("Transcript") or {}
            transcript_uri = transcript.get("TranscriptFileUri")

            if not transcript_uri:
                logger.warning("No TranscriptFileUri for job %s", job_name)
                return TranscriptionResult(segments=[])

            # Transcribe 결과 JSON 다운로드
            with urllib.request.urlopen(transcript_uri) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))

            return self._parse_speaker_segments(result_json)
        except Exception as e:
            logger.error("get_result failed for %s: %s", job_name, e)
            return TranscriptionResult(segments=[])

    @staticmethod
    def _parse_speaker_segments(result_json: dict) -> TranscriptionResult:
        """Amazon Transcribe 결과 JSON에서 화자별 세그먼트를 추출한다.

        채널 식별(ChannelIdentification) 결과가 있으면 채널별로 분리하고,
        없으면 기존 speaker_labels 파싱으로 폴백한다.
        채널 식별이 전화 통화에서 훨씬 정확하다.
        """
        results = result_json.get("results", {})

        # ── 방법 1: 채널 식별 결과 (전화 통화 최적) ──
        channel_labels = results.get("channel_labels", {})
        channels = channel_labels.get("channels", [])
        if channels:
            return AmazonTranscriber._parse_channel_segments(channels)

        # ── 방법 2: 화자 분리(diarization) 폴백 ──
        return AmazonTranscriber._parse_diarization_segments(results)

    @staticmethod
    def _parse_channel_segments(channels: list[dict]) -> TranscriptionResult:
        """채널 식별 결과를 파싱한다. 각 채널 = 각 화자 (전화 통화 시 정확도 높음).

        채널 0 = Speaker 0 (보통 발신자), 채널 1 = Speaker 1 (보통 수신자).
        시간순으로 정렬하여 대화 흐름을 재구성한다.
        """
        # 각 채널의 발화를 시간 기준으로 수집
        timed_segments: list[tuple[float, str, str]] = []  # (start_time, speaker, text)

        for channel in channels:
            channel_label = channel.get("channel_label", "ch_0")
            speaker_idx = channel_label.replace("ch_", "")
            speaker = f"Speaker {speaker_idx}"
            items = channel.get("items", [])

            current_text: list[str] = []
            segment_start: float = 0.0

            for item in items:
                content = item.get("alternatives", [{}])[0].get("content", "")
                item_type = item.get("type", "")

                if item_type == "punctuation":
                    if current_text:
                        current_text.append(content)
                    continue

                start_time = float(item.get("start_time", 0))
                end_time = float(item.get("end_time", 0))

                # 2초 이상 gap이면 새 세그먼트로 분리 (자연스러운 대화 경계)
                if current_text and start_time - segment_start > 2.0:
                    text = " ".join(current_text).strip()
                    if text:
                        timed_segments.append((segment_start, speaker, text))
                    current_text = []
                    segment_start = start_time

                if not current_text:
                    segment_start = start_time
                current_text.append(content)

            # 마지막 세그먼트
            if current_text:
                text = " ".join(current_text).strip()
                if text:
                    timed_segments.append((segment_start, speaker, text))

        # 시간순 정렬 → 대화 흐름 재구성
        timed_segments.sort(key=lambda x: x[0])

        segments = [
            SpeakerSegment(speaker_label=speaker, text=text)
            for _, speaker, text in timed_segments
        ]
        return TranscriptionResult(segments=segments)

    @staticmethod
    def _parse_diarization_segments(results: dict) -> TranscriptionResult:
        """화자 분리(speaker_labels) 결과를 파싱한다. 모노 파일 폴백용."""
        segments: list[SpeakerSegment] = []

        try:
            speaker_labels = results.get("speaker_labels", {})
            speaker_segments = speaker_labels.get("segments", [])
            items = results.get("items", [])

            if not speaker_segments and not items:
                # 화자 분리도 없으면 전체 텍스트를 단일 세그먼트로
                try:
                    full_text = results["transcripts"][0]["transcript"]
                    return TranscriptionResult(
                        segments=[SpeakerSegment(speaker_label="Speaker 0", text=full_text)]
                    )
                except (KeyError, IndexError):
                    return TranscriptionResult(segments=[])

            # 각 item에 화자 라벨을 매핑
            item_speaker_map: dict[str, str] = {}
            for seg in speaker_segments:
                speaker = seg.get("speaker_label", "spk_0")
                for item in seg.get("items", []):
                    start = item.get("start_time", "")
                    if start:
                        item_speaker_map[start] = speaker

            # 연속된 동일 화자 발화를 결합
            current_speaker: str | None = None
            current_text: list[str] = []

            for item in items:
                start_time = item.get("start_time", "")
                content = item.get("alternatives", [{}])[0].get("content", "")
                item_type = item.get("type", "")

                # punctuation은 화자 전환 없이 현재 텍스트에 붙인다
                if item_type == "punctuation":
                    if current_text:
                        current_text.append(content)
                    continue

                speaker = item_speaker_map.get(start_time, current_speaker or "spk_0")

                if speaker != current_speaker and current_speaker is not None:
                    # 화자 전환 → 이전 세그먼트 저장
                    label = current_speaker.replace("spk_", "Speaker ")
                    text = " ".join(current_text).strip()
                    if text:
                        segments.append(SpeakerSegment(speaker_label=label, text=text))
                    current_text = []

                current_speaker = speaker
                current_text.append(content)

            # 마지막 세그먼트 저장
            if current_speaker is not None and current_text:
                label = current_speaker.replace("spk_", "Speaker ")
                text = " ".join(current_text).strip()
                if text:
                    segments.append(SpeakerSegment(speaker_label=label, text=text))

        except (KeyError, IndexError, TypeError) as e:
            logger.warning("Failed to parse speaker segments: %s", str(e))
            try:
                full_text = results["transcripts"][0]["transcript"]
                segments = [SpeakerSegment(speaker_label="Speaker 0", text=full_text)]
            except (KeyError, IndexError):
                segments = []

        return TranscriptionResult(segments=segments)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_transcriber() -> Transcriber:
    """PROVIDER_MODE에 따라 적절한 Transcriber를 반환한다.

    - PROVIDER_MODE="local" → MockTranscriber
    - PROVIDER_MODE="aws"   → AmazonTranscriber
    """
    if PROVIDER_MODE == "aws":
        return AmazonTranscriber(region=AWS_REGION)
    return MockTranscriber()
