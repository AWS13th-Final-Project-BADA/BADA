from __future__ import annotations

from typing import Any

from .guardrail_service import build_legal_judgment_fallback
from .language_service import normalize_language_code


def _format_amount(amount: int | None, language: str) -> str:
    if amount is None:
        if language == "vi":
            return "số tiền cần kiểm tra"
        if language == "en":
            return "an amount that needs confirmation"
        return "확인이 필요한 금액"
    if language == "vi":
        return f"{amount:,} KRW"
    if language == "en":
        return f"{amount:,} KRW"
    return f"{amount:,}원"


def _join_items(items: list[str], language: str) -> str:
    if items:
        return ", ".join(items)
    if language == "vi":
        return "tài liệu cần kiểm tra thêm"
    if language == "en":
        return "materials that need additional review"
    return "추가 확인이 필요한 자료"


def generate_legal_judgment_fallback(
    case_context: dict[str, Any] | None = None,
    language: str = "ko",
) -> tuple[str, list[str]]:
    lang = normalize_language_code(language)
    next_actions = case_context.get("next_actions") if case_context and lang == "ko" else []
    if not next_actions:
        next_actions = _default_next_actions(lang)
    return build_legal_judgment_fallback(lang), next_actions


def generate_chat_answer(
    intent: str,
    case_context: dict[str, Any] | None,
    message: str,
    language: str,
) -> tuple[str, list[str]]:
    lang = normalize_language_code(language)
    if case_context:
        summary = case_context.get("summary", "")
        next_actions = case_context.get("next_actions", []) if lang == "ko" else []
        next_actions = next_actions or _default_next_actions(lang)
        difference = case_context.get("difference_amount")
        documents = case_context.get("documents", [])
        missing_docs = case_context.get("missing_documents", [])
        deduction_items = case_context.get("deduction_items", [])
    else:
        summary = ""
        next_actions = _default_next_actions(lang)
        difference = None
        documents = []
        missing_docs = []
        deduction_items = []

    amount = _format_amount(difference, lang)

    if lang == "vi":
        if intent == "consultation_script":
            answer = (
                "Khi đi tư vấn, bạn nên nói theo thứ tự này: trước hết là tên nơi làm việc và thời gian làm việc, "
                "sau đó là mức lương đã thỏa thuận và số tiền thực tế nhận được, rồi trình bày chênh lệch giữa bảng lương "
                f"và lịch sử chuyển khoản ({amount}). Cuối cùng, hãy hỏi về các khoản khấu trừ như "
                f"{_join_items(deduction_items, lang)}. Kết luận cuối cùng cần được cơ quan tư vấn xác nhận."
            )
        elif intent == "pack_summary":
            answer = (
                f"Điểm chính của gói tài liệu là khoản chênh lệch {amount} và danh sách chứng cứ hiện có. "
                f"Tài liệu hiện có gồm {_join_items(documents, lang)}. Tài liệu nên bổ sung gồm "
                f"{_join_items(missing_docs, lang)}. Đây không phải là kết luận pháp lý mà là phần chuẩn bị trước khi tư vấn."
            )
        else:
            answer = (
                f"Dựa trên tài liệu hiện có, có thể sắp xếp vấn đề chênh lệch {amount} để chuẩn bị tư vấn. "
                "BADA không kết luận đây là vi phạm pháp luật hay tiền lương chưa trả; kết luận cuối cùng cần được "
                "Bộ Việc làm và Lao động, trung tâm tư vấn hoặc chuyên gia xác nhận."
            )
        return answer, next_actions

    if lang == "en":
        answer = (
            f"Based on the current materials, the key point to prepare is the wage/payment difference of {amount}. "
            "BADA does not decide whether this is illegal or legally confirmed unpaid wages. Please organize the payslip, "
            "bank deposit record, employment contract, deduction items, and missing documents before consultation."
        )
        return answer, next_actions

    if intent == "pack_summary":
        answer = (
            f"이 Evidence Pack의 핵심은 {amount} 차이와 관련 자료 목록입니다. 현재 자료는 {_join_items(documents, lang)}이고, "
            f"상담 전에 보강하면 좋은 자료는 {_join_items(missing_docs, lang)}입니다. 이 내용은 확정 판단이 아니라 상담기관에서 확인할 쟁점을 정리한 것입니다."
        )
    elif intent == "consultation_script":
        answer = (
            "상담할 때는 사업장명과 근무 기간을 먼저 말하고, 약속한 임금과 실제 입금액을 설명한 뒤, "
            f"급여명세서와 입금내역 사이의 {amount} 차이를 보여주세요. 마지막으로 공제 항목과 부족한 자료를 질문하면 됩니다."
        )
    else:
        answer = (
            f"현재 자료 기준으로 {amount} 차이가 정리되어 있습니다. 이 차이의 법적 성격은 BADA가 판단하지 않고, "
            "고용노동부나 상담기관에서 확인해야 합니다. 상담 전에는 관련 자료와 질문 목록을 준비하는 것이 좋습니다."
        )
    return answer, next_actions


def _default_next_actions(language: str) -> list[str]:
    if language == "vi":
        return [
            "Sắp xếp hợp đồng lao động, bảng lương và lịch sử chuyển khoản theo cùng kỳ.",
            "Chuẩn bị ghi chú về thời gian làm việc, mức lương đã thỏa thuận và khoản khấu trừ.",
            "Hỏi trung tâm tư vấn những tài liệu còn thiếu trước khi nộp đơn.",
        ]
    if language == "en":
        return [
            "Organize the employment contract, payslip, and bank deposit record by the same period.",
            "Prepare notes about working period, promised wage, actual payment, and deductions.",
            "Ask the counseling center which missing documents should be added.",
        ]
    return [
        "근로계약서, 급여명세서, 입금내역을 같은 기간 기준으로 정리",
        "근무 기간, 약속 임금, 실제 입금액, 공제 항목을 메모",
        "상담기관에 추가로 필요한 자료를 질문",
    ]
