from __future__ import annotations

import re
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
    text = _normalize(message)

    if _has_any(
        text,
        [
            "불법",
            "위법",
            "법 위반",
            "체불 확정",
            "소송",
            "고소",
            "sue",
            "illegal",
            "violate the law",
            "bất hợp pháp",
            "trái pháp luật",
            "vi phạm pháp luật",
            "kiện",
            "tố cáo",
        ],
    ):
        return "legal_judgment_risk"

    if _has_any(
        text,
        [
            "요약",
            "핵심",
            "중요한 내용",
            "패키지에서",
            "사건 정리",
            "summary",
            "main point",
            "key point",
            "tóm tắt",
            "điểm chính",
            "nội dung quan trọng",
        ],
    ):
        return "pack_summary"

    if _has_any(
        text,
        [
            "뭐부터 말",
            "상담할 때",
            "질문 목록",
            "말해야",
            "설명하면",
            "what should i say",
            "consultation script",
            "question list",
            "nói gì",
            "nói như thế nào",
            "danh sách câu hỏi",
        ],
    ):
        return "consultation_script"

    if _has_any(
        text,
        [
            "무슨 자료",
            "누락",
            "추가 자료",
            "더 필요",
            "missing document",
            "what documents",
            "additional documents",
            "thiếu tài liệu",
            "cần thêm tài liệu",
            "tài liệu nào",
        ],
    ):
        return "missing_document_explanation"

    if _has_any(
        text,
        [
            "400,000",
            "400000",
            "차이",
            "금액",
            "입금",
            "급여명세서",
            "공제",
            "difference",
            "deduction",
            "payment",
            "payslip",
            "chênh lệch",
            "khấu trừ",
            "bảng lương",
            "chuyển khoản",
        ],
    ):
        return "amount_difference_explanation"

    if _has_any(
        text,
        [
            "쉽게",
            "베트남어",
            "영어",
            "한국어 문장",
            "번역",
            "translate",
            "plain language",
            "easy words",
            "dịch",
            "giải thích dễ hiểu",
        ],
    ):
        return "plain_language_or_translation"

    if _has_any(
        text,
        [
            "준비",
            "무엇",
            "어떻게",
            "뭘",
            "가지고",
            "가기 전에",
            "prepare",
            "before consultation",
            "what should i bring",
            "chuẩn bị",
            "trước khi tư vấn",
            "cần viết",
            "nên viết",
        ],
    ):
        return "preparation_guidance"

    if _has_any(
        text,
        [
            "충분",
            "자료",
            "없나요",
            "missing",
            "enough evidence",
            "đủ không",
            "tài liệu",
        ],
    ):
        return "missing_document_check"

    if _has_any(
        text,
        [
            "bada pack",
            "evidence pack",
            "뭐가 들어",
            "무엇",
            "목록",
            "역할",
            "gói tài liệu",
            "bằng chứng",
        ],
    ):
        return "evidence_pack_explanation"

    return "general_guidance"


def _normalize(message: str) -> str:
    return re.sub(r"\s+", " ", message.lower().strip())


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)
