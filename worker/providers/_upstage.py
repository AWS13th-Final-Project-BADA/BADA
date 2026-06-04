"""Upstage Document Parse 호출 — 정형문서(명세서·계약서·근무표·PDF) 텍스트/표 추출.

⚠️ 외부 API. 문서(이미지/PDF)가 외부로 전송된다(이미지는 마스킹 불가).
   추출된 '텍스트'를 이후 외부로 또 보내는 경우에만 security.pii.mask_pii 적용.
   엔티티 구조화는 Bedrock(내부)에서 하므로 추가 외부 전송 없음.

NOTE: 엔드포인트/응답 스키마는 Upstage 최신 문서로 확인 후 확정할 것(아래는 기본값).
      https://console.upstage.ai/docs/capabilities/document-parse
"""
from __future__ import annotations

from config import UPSTAGE_API_KEY

# TODO(확인): 현재 Document Parse 엔드포인트
_URL = "https://api.upstage.ai/v1/document-ai/document-parse"


def document_parse(file_bytes: bytes, filename: str = "document") -> str:
    """문서 → 평문 텍스트. 표/레이아웃이 포함된 텍스트를 반환."""
    import requests  # 지연 임포트

    resp = requests.post(
        _URL,
        headers={"Authorization": f"Bearer {UPSTAGE_API_KEY}"},
        files={"document": (filename, file_bytes)},
        data={"output_formats": "['text']"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # 응답 형태는 버전에 따라 다를 수 있음 — text 우선, 없으면 content.text
    if isinstance(data, dict):
        if data.get("text"):
            return data["text"]
        content = data.get("content") or {}
        if isinstance(content, dict) and content.get("text"):
            return content["text"]
    return str(data)
