from __future__ import annotations

from typing import Literal


Intent = Literal[
    "pack_summary",
    "consultation_script",
    "missing_document_explanation",
    "amount_difference_explanation",
    "plain_language_or_translation",
    "preparation_guidance",
    "missing_document_check",
    "evidence_pack_explanation",
    "legal_judgment_risk",
    "general_guidance",
]


def classify_intent(message: str) -> Intent:
    text = message.lower().strip()

    legal_phrases = [
        "불법",
        "위법",
        "체불임금",
        "무조건 받을",
        "사업주가 법",
        "소송",
        "확정",
    ]
    if any(phrase in text for phrase in legal_phrases):
        return "legal_judgment_risk"

    if any(phrase in text for phrase in ["한 문단", "요약", "중요한 내용", "핵심", "패키지에서", "사건을 정리"]):
        return "pack_summary"

    if any(phrase in text for phrase in ["뭐부터 말", "순서", "상담하러", "상담 때", "질문 목록", "보여줄 문장", "말하면"]):
        return "consultation_script"

    if any(phrase in text for phrase in ["왜 필요", "무슨 뜻", "누락된", "누락 자료", "추가 자료", "더 준비"]):
        return "missing_document_explanation"

    if any(phrase in text for phrase in ["400,000", "400000", "차이", "금액", "입금액", "급여명세서", "공제"]):
        return "amount_difference_explanation"

    if any(phrase in text for phrase in ["쉽게", "베트남어", "영어", "한국어 문장", "번역", "보여줘요"]):
        return "plain_language_or_translation"

    if any(phrase in text for phrase in ["준비", "무엇", "어떻게", "뭘", "가지", "가기 전에"]):
        return "preparation_guidance"

    if any(phrase in text for phrase in ["충분", "자료", "누락", "더 필요", "없나요", "가도 될까요"]):
        return "missing_document_check"

    if any(phrase in text for phrase in ["bada pack", "evidence pack", "들어가", "무엇", "목록", "어땠"]):
        return "evidence_pack_explanation"

    return "general_guidance"
