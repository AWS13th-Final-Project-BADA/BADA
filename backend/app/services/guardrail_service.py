from __future__ import annotations

import re

from .language_service import normalize_language_code


FORBIDDEN_PATTERNS = [
    # Korean final legal conclusions.
    r"불법입니다",
    r"위법입니다",
    r"법(?:을)?\s*위반했습니다",
    r"체불(?:임금)?(?:이)?\s*확정(?:되었습니다|입니다)",
    r"미지급(?:이)?\s*확정(?:되었습니다|입니다)",
    r"확정\s*금액(?:은|입니다)",
    r"무조건\s*받을\s*수\s*있습니다",
    r"반드시\s*받을\s*수\s*있습니다",
    r"바로\s*신고하세요",
    r"즉시\s*신고하세요",
    r"소송하세요",
    r"고소하세요",
    r"사업주(?:는|가).*(처벌|벌금|감옥)",
    # English final legal conclusions.
    r"\bit\s+is\s+illegal\b",
    r"\bthis\s+is\s+illegal\b",
    r"\bthe\s+employer\s+(has\s+)?violated\s+the\s+law\b",
    r"\bunpaid\s+wages\s+(are|is)\s+confirmed\b",
    r"\byou\s+will\s+definitely\s+(receive|get)\b",
    r"\byou\s+are\s+guaranteed\s+to\s+(receive|get)\b",
    r"\breport\s+(it\s+)?immediately\b",
    r"\bsue\s+(the\s+employer|them)\b",
    r"\bfile\s+a\s+lawsuit\b",
    # Vietnamese final legal conclusions.
    r"đây\s+là\s+(hành\s+vi\s+)?(bất\s+hợp\s+pháp|trái\s+pháp\s+luật)",
    r"chủ\s+(sử\s+dụng\s+lao\s+động\s+)?đã\s+vi\s+phạm\s+pháp\s+luật",
    r"công\s+ty\s+đã\s+vi\s+phạm\s+pháp\s+luật",
    r"tiền\s+lương\s+bị\s+nợ\s+đã\s+được\s+xác\s+nhận",
    r"bạn\s+chắc\s+chắn\s+sẽ\s+(nhận|lấy)\s+được",
    r"bạn\s+được\s+đảm\s+bảo\s+sẽ\s+(nhận|lấy)\s+được",
    r"hãy\s+(tố\s+cáo|báo\s+cáo|kiện)\s+ngay",
    r"nộp\s+đơn\s+kiện\s+ngay",
]


def contains_forbidden_text(answer: str) -> bool:
    normalized = re.sub(r"\s+", " ", answer.lower().strip())
    return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS)


def apply_output_guardrail(answer: str, language: str = "ko") -> tuple[str, str, bool]:
    if contains_forbidden_text(answer):
        return build_legal_judgment_fallback(language), "failed", True
    return answer, "passed", False


def build_legal_judgment_fallback(language: str = "ko") -> str:
    lang = normalize_language_code(language)
    if lang == "vi":
        return (
            "Câu hỏi này cần đánh giá pháp lý. BADA là dịch vụ sắp xếp tài liệu trước khi tư vấn, "
            "không kết luận có vi phạm pháp luật hay xác định bản chất pháp lý của khoản chênh lệch lương. "
            "Kết luận cuối cùng cần được xác nhận bởi Bộ Việc làm và Lao động, trung tâm tư vấn hoặc chuyên gia. "
            "Tôi có thể giúp bạn chuẩn bị tài liệu, tóm tắt sự việc và danh sách câu hỏi để đi tư vấn."
        )
    if lang == "en":
        return (
            "This question requires legal judgment. BADA organizes materials before consultation and does not decide "
            "whether the employer violated the law or whether a wage difference is legally confirmed. "
            "The final judgment should be confirmed by the Ministry of Employment and Labor, a counseling center, "
            "or a qualified expert. I can still help you prepare documents, a case summary, and consultation questions."
        )
    return (
        "이 질문은 법률 판단이 필요합니다. BADA는 상담 전 자료 정리 서비스이며, 법 위반 여부나 임금 차액의 법적 성격을 판단하지 않습니다. "
        "최종 판단은 고용노동부, 상담기관 또는 전문가 상담을 통해 확인해야 합니다. "
        "다만 현재 자료 기준으로 상담 전 준비자료, 사건 요약, 질문 목록은 도와드릴 수 있습니다."
    )


def build_disclaimer(language: str = "ko") -> str:
    lang = normalize_language_code(language)
    if lang == "vi":
        return (
            "Câu trả lời này không phải là đánh giá pháp lý. Đây là hướng dẫn chuẩn bị trước khi tư vấn, "
            "dựa trên tài liệu bạn cung cấp và tài liệu hướng dẫn chính thức. Kết luận cuối cùng cần được xác nhận "
            "qua Bộ Việc làm và Lao động, trung tâm tư vấn hoặc chuyên gia."
        )
    if lang == "en":
        return (
            "This answer is not legal judgment. It is preparation guidance based on the materials you provided "
            "and official reference documents. The final judgment should be confirmed through the Ministry of Employment "
            "and Labor, a counseling center, or a qualified expert."
        )
    return (
        "이 답변은 법률 판단이 아니라, 사용자가 제공한 자료와 공식 안내문을 바탕으로 한 상담 전 준비 안내입니다. "
        "최종 판단은 고용노동부, 상담기관 또는 전문가 상담을 통해 확인해야 합니다."
    )
