"""OCR provider — 이미지/문서 → 텍스트·엔티티. 라우팅은 카테고리 기준(tech.md).

담당: OCR 기능.
- 정형(contract/statement/schedule/payment-pdf) → UpstageOcr (PII 마스킹 후 호출)
- 비정형(chat/other/사진/앱캡처)            → ClaudeVisionOcr
출력은 dict {"raw_text": str, "entities": {...}} (backend OcrResult 스키마와 호환).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config import PROVIDER_MODE

# tech.md 라우팅 규칙
STRUCTURED = {"contract", "statement", "schedule"}  # payment는 PDF면 정형, 앱캡처면 비정형(담당자 판단)


class OcrProvider(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, category: str) -> dict:
        """반환: {"raw_text": str, "entities": dict}. 판단·계산 금지."""


class MockOcr(OcrProvider):
    """로컬 기본값. 실제 이미지가 없으므로 빈 추출을 반환(숫자는 사용자 입력 경로 사용)."""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        return {"raw_text": "", "entities": {}}


class ClaudeVisionOcr(OcrProvider):
    """담당자 구현 지점 — Bedrock Vision + Pydantic 스키마 강제 + 재시도(architecture.md)."""

    def extract(self, image_bytes: bytes, category: str) -> dict:  # pragma: no cover
        raise NotImplementedError("Bedrock Vision 호출 + OcrResult 스키마 검증 구현")


class UpstageOcr(OcrProvider):
    """담당자 구현 지점 — 외부 API. 전송 전 security.pii.mask_pii 적용 필수."""

    def extract(self, image_bytes: bytes, category: str) -> dict:  # pragma: no cover
        raise NotImplementedError("Upstage 호출 구현 (PII 마스킹 후 전송)")


def get_ocr(category: str) -> OcrProvider:
    if PROVIDER_MODE != "aws":
        return MockOcr()
    return UpstageOcr() if category in STRUCTURED else ClaudeVisionOcr()
