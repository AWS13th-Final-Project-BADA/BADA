"""PII 마스킹 — Upstage(외부 API) 전송 사본에만 적용(security.md).

Bedrock(AWS 신뢰경계 내)에는 적용하지 않는다. DB 원본은 무수정 보존.
정규식 기반(MVP). Presidio/Comprehend 고도화는 Phase 2.
"""
from __future__ import annotations

import re

# 주민등록번호: 6자리-7자리
_RRN = re.compile(r"\b\d{6}-\d{7}\b")
# 전화번호: 010-xxxx-xxxx 등
_PHONE = re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")
# 계좌번호: 숫자 그룹이 하이픈으로 연결된 형태
_ACCOUNT = re.compile(r"\b\d{2,6}-\d{2,6}-\d{2,8}(?:-\d{1,8})?\b")


def mask_pii(text: str) -> str:
    """순서 중요: 구체적 패턴(주민→전화)을 먼저, 일반 패턴(계좌)을 마지막에."""
    if not text:
        return text
    text = _RRN.sub("[RRN]", text)          # 1) 주민번호 (가장 구체적)
    text = _PHONE.sub("[PHONE]", text)      # 2) 전화 (계좌 패턴이 삼키지 않게 먼저)
    text = _ACCOUNT.sub("[ACCOUNT]", text)  # 3) 계좌 (가장 일반적)
    return text
