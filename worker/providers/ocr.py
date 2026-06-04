"""OCR provider — 이미지/문서 → 텍스트·엔티티. 카테고리 기준 하이브리드 라우팅(tech.md).

- 정형(contract/statement/schedule) → Upstage(텍스트 추출) → Claude Text(엔티티 구조화)
- 비정형(chat/other/사진/앱캡처)     → Claude Vision(이미지→엔티티 1샷)
- 애매                              → Claude Vision (안전 기본값)

출력: {"raw_text": str, "entities": dict}  (schema.OcrResult 검증 통과본)
판단·계산 금지 — 읽기/구조화만(architecture.md).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config import PROVIDER_MODE

STRUCTURED = {"contract", "statement", "schedule"}

_SYSTEM = (
    "당신은 임금체불 사건 증거에서 텍스트와 엔티티를 추출하는 도우미입니다. "
    "읽어서 구조화만 하고 위법 여부·금액을 판단하지 마세요. "
    "보이지 않는 값은 지어내지 말고, 불확실하면 confidence를 low로 표기하세요. "
    "반드시 유효한 JSON만 출력하세요."
)


def _instruction(category: str) -> str:
    from llm.prompts import load
    try:
        return load("extraction").replace("{{category}}", category)
    except Exception:
        return (f"카테고리: {category}. 이미지/문서의 모든 텍스트(raw_text)와 엔티티"
                "(dates, amounts[label,value], hourly_wage, monthly_wage, hours, "
                "deductions[name,amount], workplace_name, employer_name, pay_date, "
                "utterances[speaker,text,kind])를 JSON으로 추출하세요. 금액은 정수.")


class OcrProvider(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, category: str) -> dict:
        ...


class MockOcr(OcrProvider):
    """로컬 기본값. 실제 이미지 추출 없음 → 빈 결과(숫자는 사용자 입력 경로 사용)."""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        return {"raw_text": "", "entities": {}}


class ClaudeVisionOcr(OcrProvider):
    """이미지 → Bedrock Claude Vision → 엔티티(1샷). Pydantic 검증+재시도."""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        from providers import _bedrock
        from providers.schema import OcrResult
        blocks = [
            _bedrock.image_block(image_bytes, _bedrock.media_type_of(image_bytes)),
            _bedrock.text_block(_instruction(category)),
        ]
        res = _bedrock.extract_json(_SYSTEM, blocks, OcrResult)
        return {"raw_text": res.raw_text, "entities": res.entities.model_dump()}


class UpstageOcr(OcrProvider):
    """정형문서 → Upstage(텍스트/표) → Bedrock Claude Text(엔티티 구조화). 2단계."""

    def extract(self, image_bytes: bytes, category: str) -> dict:
        from providers import _bedrock, _upstage
        from providers.schema import OcrResult
        text = _upstage.document_parse(image_bytes)
        blocks = [_bedrock.text_block(_instruction(category) + "\n\n[문서 텍스트]\n" + text)]
        res = _bedrock.extract_json(_SYSTEM, blocks, OcrResult)
        return {"raw_text": text, "entities": res.entities.model_dump()}


def get_ocr(category: str) -> OcrProvider:
    if PROVIDER_MODE != "aws":
        return MockOcr()
    return UpstageOcr() if category in STRUCTURED else ClaudeVisionOcr()
