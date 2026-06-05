from __future__ import annotations

from typing import Tuple

FORBIDDEN_PHRASES = [
    "불법입니다",
    "위법입니다",
    "사업주가 법을 위반했습니다",
    "체불임금이 확정되었습니다",
    "무조건 받을 수 있습니다",
    "반드시 받을 수 있습니다",
    "바로 신고하세요",
    "소송하세요",
    "확정 금액은",
]

FALLBACK_ANSWER = (
    "이 질문은 법률 판단을 필요로 합니다. BADA는 신고 전 자료 정리 서비스이며, 법 위반 여부나 임금 차액의 법적 성격을 판단하지 않습니다. "
    "최종 판단은 고용노동부, 상담기관 또는 전문가 상담을 통해 확인해야 합니다. "
    "하지만 현재 자료 기준으로 준비할 수 있는 사항을 안내해 드릴 수 있습니다."
)


def contains_forbidden_text(answer: str) -> bool:
    normalized = answer.lower()
    return any(phrase in normalized for phrase in FORBIDDEN_PHRASES)


def apply_output_guardrail(answer: str) -> tuple[str, str, bool]:
    if contains_forbidden_text(answer):
        return FALLBACK_ANSWER, "failed", True
    return answer, "passed", False


def build_disclaimer() -> str:
    return (
        "이 답변은 법률 판단이 아니라, 사용자가 제공한 자료와 공식 안내문을 바탕으로 한 상담 전 준비 안내입니다. "
        "최종 판단은 고용노동부, 상담기관 또는 전문가 상담을 통해 확인해야 합니다."
    )
