"""Upstage Document Parse — 정형문서(명세서·계약서·근무표·PDF통장) OCR.

⚠️ 외부 API. 전송 전 반드시 PII 마스킹(security.md).
"""
from __future__ import annotations

from ..security.pii import mask_pii


def parse_document(text_or_bytes, *, pre_extracted_text: str | None = None):  # pragma: no cover - W2
    """Upstage 호출. 텍스트성 입력은 mask_pii로 먼저 마스킹한 사본을 전송한다."""
    if pre_extracted_text is not None:
        safe = mask_pii(pre_extracted_text)  # 외부로 나가는 사본만 마스킹
        # TODO(W2): Upstage API 호출(safe 전송). DB 원본은 무수정 보존.
        _ = safe
    raise NotImplementedError("W2 bolt: Upstage Document Parse 호출 구현")
