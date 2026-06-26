"""Bedrock Claude — Vision(OCR+엔티티) / Text(문장화·요약).

핵심: 출력을 Pydantic 스키마로 강제하고, 실패 시 재시도(architecture.md).
실제 호출은 providers/_bedrock.py 공통 헬퍼를 통한다.
"""
from __future__ import annotations

import json


class SchemaValidationError(Exception):
    pass


def invoke_vision_with_schema(prompt: str, image_bytes: bytes, schema_model, *, max_retries: int = 2):
    """이미지 → Claude Vision → JSON → schema_model 검증. 실패하면 재시도.

    절대 임의 값을 지어내지 않는다. 최종 실패 시 예외 → 호출부에서 ocr_status='failed'.
    """
    from providers import _bedrock

    system = (
        "당신은 임금체불 사건 증거에서 텍스트와 엔티티를 추출하는 도우미입니다. "
        "읽어서 구조화만 하고 위법 여부·금액을 판단하지 마세요. "
        "보이지 않는 값은 지어내지 말고, 불확실하면 confidence를 low로 표기하세요. "
        "반드시 유효한 JSON만 출력하세요."
    )
    blocks = [
        _bedrock.file_block(image_bytes),
        _bedrock.text_block(prompt),
    ]
    try:
        return _bedrock.extract_json(system, blocks, schema_model, max_retries=max_retries)
    except Exception as e:
        raise SchemaValidationError(str(e)) from e


def invoke_text(prompt: str, *, system: str | None = None, max_tokens: int = 800) -> str:
    """타임라인 문장화·요약. 계산값을 만들지 않고 주어진 사실을 문장으로만 정리."""
    from providers import _bedrock

    _system = system or (
        "주어진 사실을 자연스러운 한국어로 정리하세요. "
        "사실을 추가하거나 판단하지 마세요. "
        "금지 표현(불법/확정/무조건/바로 신고)을 쓰지 말고, "
        "미지급 '의심'·'확인 필요' 톤만 사용하세요."
    )
    return _bedrock.invoke(_system, [_bedrock.text_block(prompt)], max_tokens=max_tokens)
