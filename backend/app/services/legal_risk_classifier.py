from __future__ import annotations

from typing import Tuple


def classify_legal_risk(message: str) -> Tuple[str, bool]:
    text = message.lower().strip()

    blocked_phrases = [
        "불법",
        "위법",
        "사업주가 법",
        "무조건 받을",
        "반드시 받을",
        "체불임금",
        "확정",
        "바로 신고",
        "소송",
    ]
    for phrase in blocked_phrases:
        if phrase in text:
            return "blocked", True

    review_phrases = [
        "상담 가도 될까요",
        "충분한가요",
        "가능성이 있나요",
        "받을 가능성",
        "검토해 주세요",
        "점검",
    ]
    for phrase in review_phrases:
        if phrase in text:
            return "review", False

    return "safe", False
