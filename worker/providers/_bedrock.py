"""Bedrock Claude 호출 헬퍼 — 메시지 API + 이미지/PDF 블록 + JSON 스키마 강제/재시도.

OCR(Vision)과 Upstage/Parseur 후처리(Text 구조화)가 공유한다.
"""
from __future__ import annotations

import base64
import json

from config import AWS_REGION, BEDROCK_MODEL_ID

_client = None


def _bedrock():
    global _client
    if _client is None:
        import boto3  # 지연 임포트 (로컬 모드에서 미설치 허용)
        _client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _client


def text_block(t: str) -> dict:
    return {"type": "text", "text": t}


def image_block(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                        "data": base64.b64encode(image_bytes).decode()}}


def document_block(pdf_bytes: bytes, title: str = "document") -> dict:
    """PDF 입력용 document 블록 (Claude 3.5+/4 지원)."""
    return {"type": "document", "title": title,
            "source": {"type": "base64", "media_type": "application/pdf",
                       "data": base64.b64encode(pdf_bytes).decode()}}


def is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def media_type_of(data: bytes) -> str:
    if data[:8].startswith(b"\x89PNG"):
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def file_block(data: bytes, title: str = "document") -> dict:
    """파일 바이트 → PDF면 document, 아니면 image 블록 자동 선택."""
    return document_block(data, title) if is_pdf(data) else image_block(data, media_type_of(data))


def invoke(system: str, content_blocks: list[dict], max_tokens: int = 2000) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": content_blocks}],
    }
    r = _bedrock().invoke_model(modelId=BEDROCK_MODEL_ID, body=json.dumps(body))
    payload = json.loads(r["body"].read())
    return payload["content"][0]["text"]


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    return s.strip()


def extract_json(system: str, content_blocks: list[dict], schema_model, max_retries: int = 2):
    """응답을 JSON 파싱 + schema_model 검증. 실패 시 재시도. 끝까지 실패하면 예외.

    절대 값을 지어내지 않는다(architecture.md). 최종 실패는 호출부에서 ocr_status=failed 처리.
    """
    last = None
    blocks = list(content_blocks)
    for _ in range(max_retries + 1):
        raw = invoke(system, blocks, max_tokens=8000)   # 긴 문서도 안 잘리게 충분히
        try:
            return schema_model.model_validate(json.loads(_strip_fences(raw)))
        except Exception as e:
            last = e
            blocks = blocks + [text_block(
                "이전 출력이 잘렸거나 JSON 형식이 아니었습니다. 반드시 유효한 JSON 하나만 출력하고, "
                "raw_text는 핵심만 800자 이내로 줄이세요.")]
    raise ValueError(f"schema validation failed after retries: {last}")
