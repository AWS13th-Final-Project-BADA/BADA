"""Bedrock Claude — Vision(OCR+엔티티) / Text(문장화·요약).

핵심: 출력을 Pydantic 스키마로 강제하고, 실패 시 재시도(architecture.md).
실제 호출은 W2 bolt에서 완성. 여기선 인터페이스 + 재시도 골격.
"""
from __future__ import annotations

import json

import boto3

# backend 스키마 재사용 (모노레포 공유). 경로는 배포 시 패키징으로 정리.
# from backend.app.schemas import OcrResult


class SchemaValidationError(Exception):
    pass


def _client(region: str = "ap-northeast-2"):
    return boto3.client("bedrock-runtime", region_name=region)


def invoke_vision_with_schema(prompt: str, image_bytes: bytes, schema_model, *, max_retries: int = 2):
    """이미지 → Claude Vision → JSON → schema_model 검증. 실패하면 재시도.

    절대 임의 값을 지어내지 않는다. 최종 실패 시 예외 → 호출부에서 ocr_status='failed'.
    """
    last_err = None
    for attempt in range(max_retries + 1):
        raw = _call_vision(prompt, image_bytes)  # TODO(W2): 실제 Bedrock 호출
        try:
            data = json.loads(raw)
            return schema_model.model_validate(data)
        except Exception as e:  # JSON/스키마 실패
            last_err = e
            prompt = prompt + "\n\n반드시 유효한 JSON만 출력하세요. 이전 출력이 형식에 맞지 않았습니다."
    raise SchemaValidationError(str(last_err))


def _call_vision(prompt: str, image_bytes: bytes) -> str:  # pragma: no cover - W2에서 구현
    raise NotImplementedError("W2 bolt: Bedrock Vision 호출 구현")


def invoke_text(prompt: str) -> str:  # pragma: no cover - W2에서 구현
    """타임라인 문장화·요약. 계산값을 만들지 않고 주어진 사실을 문장으로만 정리."""
    raise NotImplementedError("W2 bolt: Bedrock Text 호출 구현")
