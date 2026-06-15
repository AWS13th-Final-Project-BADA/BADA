from __future__ import annotations

from .language_service import normalize_language_code


VIETNAMESE_GLOSSARY = {
    "급여명세서": "bảng lương",
    "임금명세서": "bảng lương",
    "입금내역": "lịch sử chuyển khoản",
    "계좌 입금내역": "lịch sử chuyển khoản ngân hàng",
    "근로계약서": "hợp đồng lao động",
    "고용노동부": "Bộ Việc làm và Lao động",
    "법무부": "Bộ Tư pháp",
    "상담기관": "trung tâm tư vấn",
    "외국인력상담센터": "Trung tâm tư vấn lao động nước ngoài",
    "진정서": "đơn khiếu nại",
    "대지급금": "khoản thanh toán thay thế",
    "체불 임금": "tiền lương bị nợ",
    "체불임금": "tiền lương bị nợ",
    "공제 항목": "khoản khấu trừ",
    "기숙사비": "phí ký túc xá",
    "식비": "tiền ăn",
    "작업복비": "phí đồng phục lao động",
    "출퇴근 기록": "hồ sơ chấm công",
    "근무시간 기록": "ghi chép thời gian làm việc",
    "사업장": "nơi làm việc",
    "사업주": "chủ sử dụng lao động",
    "근로자": "người lao động",
    "사용자": "người sử dụng lao động",
    "근로기준법": "Luật Tiêu chuẩn lao động",
    "임금채권보장법": "Luật Bảo đảm yêu cầu tiền lương",
}


def annotate_terms_for_language(text: str | None, language: str) -> str:
    if not text:
        return ""

    lang = normalize_language_code(language)
    if lang != "vi":
        return text

    annotated = text
    for korean, translated in sorted(VIETNAMESE_GLOSSARY.items(), key=lambda item: len(item[0]), reverse=True):
        annotated = _annotate_once(annotated, korean, translated)
    return annotated


def _annotate_once(text: str, korean: str, translated: str) -> str:
    replacement = f"{korean}({translated})"
    if replacement in text:
        return text

    result: list[str] = []
    cursor = 0
    term_length = len(korean)
    while True:
        idx = text.find(korean, cursor)
        if idx == -1:
            result.append(text[cursor:])
            break

        result.append(text[cursor:idx])
        after = idx + term_length
        if after < len(text) and text[after] == "(":
            result.append(korean)
        else:
            result.append(replacement)
        cursor = after

    return "".join(result)
