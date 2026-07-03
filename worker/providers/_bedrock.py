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


# Claude Vision은 긴 변 ~1568px를 넘는 해상도에서 정확도 이득이 거의 없고 입력 토큰·지연만
# 늘어난다. 큰 사진을 이 상한으로 축소하면 vision 호출 지연/비용이 줄어든다(모델·프롬프트 불변).
_VISION_MAX_SIDE = 1568
_VISION_JPEG_QUALITY = 85


def downscale_image(data: bytes, max_side: int = _VISION_MAX_SIDE, quality: int = _VISION_JPEG_QUALITY) -> bytes:
    """이미지가 max_side보다 크면 종횡비 유지로 축소 후 JPEG 재인코딩. 불필요/실패 시 원본 반환.

    안전 원칙: PIL 미설치·디코드 실패·기타 예외에서는 원본 바이트를 그대로 반환하여
    OCR 자체가 절대 깨지지 않도록 한다(다운스케일은 최적화이지 필수 경로가 아니다).
    """
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(data)) as img:
            w, h = img.size
            if max(w, h) <= max_side:
                return data  # 이미 충분히 작음 → 원본 유지(재인코딩 안 함)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            scale = max_side / float(max(w, h))
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            return buf.getvalue()
    except Exception:
        return data


def file_block(data: bytes, title: str = "document") -> dict:
    """파일 바이트 → PDF면 document, 아니면 (필요 시 축소된) image 블록 자동 선택."""
    if is_pdf(data):
        return document_block(data, title)
    reduced = downscale_image(data)
    # 축소·재인코딩됐으면 JPEG, 원본 유지면 원본 media type 감지.
    media = "image/jpeg" if reduced is not data else media_type_of(data)
    return image_block(reduced, media)


def invoke(system: str, content_blocks: list[dict], max_tokens: int = 2000) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": content_blocks}],
    }
    try:
        from metrics import track_bedrock
    except ImportError:
        track_bedrock = None

    if track_bedrock:
        with track_bedrock("invoke"):
            r = _bedrock().invoke_model(modelId=BEDROCK_MODEL_ID, body=json.dumps(body))
    else:
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
    import logging
    _log = logging.getLogger("worker.bedrock")
    last = None
    blocks = list(content_blocks)
    for attempt in range(max_retries + 1):
        raw = invoke(system, blocks, max_tokens=8000)   # 긴 문서도 안 잘리게 충분히
        stripped = _strip_fences(raw)
        _log.info("Bedrock 응답 (attempt=%d, len=%d): %s", attempt, len(stripped), stripped[:500])
        try:
            data = json.loads(stripped)
            # 모델이 entities 래핑 없이 flat하게 줄 때 흡수 (raw_text 외 전부를 entities로).
            # 일부 프롬프트(카톡 등)는 중첩 구조를 지시하지 않아 모델이 평평하게 출력 →
            # 이 정규화가 없으면 OcrResult가 raw_text만 건지고 entities를 통째로 버림.
            if isinstance(data, dict) and "raw_text" in data and "entities" not in data:
                _rt = data.pop("raw_text", "")
                data = {"raw_text": _rt, "entities": data}
            result = schema_model.model_validate(data)
            _log.info("Pydantic 검증 성공: entities keys=%s", list((result.entities.model_dump() if hasattr(result, 'entities') else {}).keys())[:5])
            return result
        except Exception as e:
            last = e
            _log.warning("Pydantic 검증 실패 (attempt=%d): %s", attempt, str(e)[:200])
            blocks = blocks + [text_block(
                "이전 출력이 잘렸거나 JSON 형식이 아니었습니다. 반드시 유효한 JSON 하나만 출력하고, "
                "raw_text는 핵심만 800자 이내로 줄이세요.")]
    raise ValueError(f"schema validation failed after retries: {last}")
