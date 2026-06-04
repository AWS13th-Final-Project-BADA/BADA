"""Upstage Document Parse 호출 — 정형문서(명세서·계약서·근무표·PDF) 텍스트/표 추출.

⚠️ 외부 API. 문서(이미지/PDF)가 외부로 전송된다(이미지는 마스킹 불가).
   엔티티 구조화는 Bedrock(내부)에서 하므로 추가 외부 전송 없음.

API: https://console.upstage.ai/docs/capabilities/document-digitization/document-parsing
지원: PDF, PNG, JPG, JPEG, TIFF, BMP, GIF, WEBP, DOCX, PPTX, XLSX, HWP
"""
from __future__ import annotations

import time

from config import UPSTAGE_API_KEY

_URL = "https://api.upstage.ai/v1/document-ai/document-parse"
_MAX_RETRY = 3          # 429(rate limit) 재시도 횟수
_BACKOFF = 3            # 초


def document_parse(file_bytes: bytes, filename: str = "document") -> str:
    """문서 → 평문 텍스트. 429(요청 한도)는 백오프 후 재시도. 최종 실패 시 예외."""
    import requests  # 지연 임포트

    if not UPSTAGE_API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY 미설정 (.env)")

    last = None
    for attempt in range(_MAX_RETRY):
        resp = requests.post(
            _URL,
            headers={"Authorization": f"Bearer {UPSTAGE_API_KEY}"},
            files={"document": (filename, file_bytes)},
            data={"model": "document-parse", "output_formats": "['text', 'markdown']"},
            timeout=90,
        )
        if resp.status_code == 429:
            last = resp
            time.sleep(_BACKOFF * (attempt + 1))  # 3s, 6s, 9s
            continue
        resp.raise_for_status()
        return _extract_text(resp.json())

    # 재시도 소진
    if last is not None:
        last.raise_for_status()
    raise RuntimeError("Upstage 호출 실패")


def _extract_text(data: dict) -> str:
    """Document Parse 응답에서 텍스트 추출. 버전별 형태(content.text/markdown/html, elements)를 흡수."""
    if not isinstance(data, dict):
        return str(data)

    content = data.get("content")
    if isinstance(content, dict):
        for k in ("text", "markdown", "html"):
            if content.get(k):
                return content[k]
    if isinstance(content, str) and content:
        return content

    for k in ("text", "markdown"):
        if data.get(k):
            return data[k]

    elements = data.get("elements")
    if isinstance(elements, list):
        parts = []
        for el in elements:
            c = (el or {}).get("content") if isinstance(el, dict) else None
            if isinstance(c, dict):
                parts.append(c.get("text") or c.get("markdown") or "")
            elif isinstance(c, str):
                parts.append(c)
        joined = "\n".join(p for p in parts if p)
        if joined:
            return joined

    return str(data)
