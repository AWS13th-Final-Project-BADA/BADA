from __future__ import annotations

from typing import Any


def _format_amount(amount: int) -> str:
    return f"{amount:,}원"


def _join_items(items: list[str]) -> str:
    return ", ".join(items) if items else "추가 확인이 필요한 자료"


def generate_legal_judgment_fallback(case_context: dict[str, Any] | None = None) -> tuple[str, list[str]]:
    next_actions = case_context.get("next_actions") if case_context else []
    if not next_actions:
        next_actions = [
            "수집한 자료를 정리하고 상담기관과 상의하세요.",
            "BADA는 신고 전 자료 정리 서비스입니다.",
        ]

    answer = (
        "이 질문은 법률 판단을 필요로 합니다. BADA는 신고 전 자료 정리 서비스이며, 법 위반 여부나 임금 차액의 법적 성격을 판단하지 않습니다. "
        "최종 판단은 고용노동부, 상담기관 또는 전문가 상담을 통해 확인해야 합니다. "
        "하지만 현재 자료 기준으로 준비할 수 있는 사항을 안내해 드릴 수 있습니다."
    )
    return answer, next_actions


def generate_chat_answer(
    intent: str,
    case_context: dict[str, Any] | None,
    message: str,
    language: str,
) -> tuple[str, list[str]]:
    if case_context:
        missing_docs = case_context.get("missing_documents", [])
        summary = case_context.get("summary", "현재 자료 기준으로 준비 상태를 확인합니다.")
        next_actions = case_context.get("next_actions", [])
        difference = case_context.get("difference_amount")
        documents = case_context.get("documents", [])
        deduction_items = case_context.get("deduction_items", [])
    else:
        missing_docs = []
        summary = "제공된 자료를 바탕으로 상담 전 준비사항을 안내합니다."
        next_actions = [
            "수집한 증거를 정리하고 상담기관과 함께 검토하세요.",
            "필요한 자료를 추가로 준비하세요.",
        ]
        difference = None
        documents = []
        deduction_items = []

    if intent == "pack_summary":
        answer = (
            f"이 Evidence Pack의 핵심은 { _format_amount(difference) if difference is not None else '확인이 필요한 금액' } 차이와 "
            f"관련 자료 목록입니다. 현재 정리된 자료는 { _join_items(documents) }이고, "
            f"상담 전에 더 보강하면 좋은 자료는 { _join_items(missing_docs) }입니다. "
            "이 내용은 확정 판단이 아니라 상담기관에서 확인할 쟁점을 보기 쉽게 묶은 것입니다."
        )
    elif intent == "consultation_script":
        answer = (
            "상담할 때는 다음 순서로 설명하면 좋습니다. "
            "먼저 근무한 기간과 사업장 정보를 말하고, 그다음 약속한 임금과 실제 입금액을 보여주세요. "
            f"이후 급여명세서와 입금내역 사이에 { _format_amount(difference) if difference is not None else '확인이 필요한' } 차이가 있다고 설명하고, "
            f"마지막으로 공제 항목({ _join_items(deduction_items) })과 추가로 준비 중인 자료를 말하면 됩니다. "
            "최종 판단은 상담기관에서 확인해야 합니다."
        )
        next_actions = [
            "근무기간, 약속 임금, 실제 입금액 순서로 말할 준비",
            "급여명세서와 입금내역을 나란히 보여줄 준비",
            "공제 항목과 누락 자료를 마지막에 질문",
        ]
    elif intent == "missing_document_explanation":
        if missing_docs:
            answer = (
                f"현재 패키지에서 더 준비하면 좋은 자료는 { _join_items(missing_docs) }입니다. "
                "이 자료들은 상담기관이 근무시간, 공제 설명, 사업장 정보를 더 정확히 확인하는 데 도움이 됩니다. "
                "자료가 없더라도 지금 있는 자료를 먼저 정리해서 상담받고, 상담기관이 요청하는 자료를 추가로 준비할 수 있습니다."
            )
        else:
            answer = (
                "현재 샘플 패키지 기준으로는 뚜렷한 누락 자료를 더 특정하기 어렵습니다. "
                "상담 전에는 원본에 가까운 계약서, 급여명세서, 입금내역, 대화 캡처를 함께 준비해 두면 좋습니다."
            )
    elif intent == "amount_difference_explanation":
        answer = (
            f"패키지에는 급여명세서에 적힌 금액과 실제 입금된 금액 사이에 { _format_amount(difference) if difference is not None else '확인이 필요한 금액' } 차이가 정리되어 있습니다. "
            "이 차이는 바로 확정 금액이라는 뜻이 아니라, 상담기관에서 원인과 근거를 확인해야 하는 항목입니다. "
            "상담할 때는 급여명세서, 입금내역, 공제 설명 자료를 함께 보여주면 좋습니다."
        )
    elif intent == "plain_language_or_translation":
        answer = (
            "상담원에게 이렇게 보여줄 수 있습니다. "
            f"\"제가 준비한 자료에는 급여명세서와 실제 입금내역 사이에 { _format_amount(difference) if difference is not None else '금액' } 차이가 있습니다. "
            f"공제 항목은 { _join_items(deduction_items) }로 정리되어 있고, "
            f"추가로 확인할 자료는 { _join_items(missing_docs) }입니다. 이 차이가 어떤 의미인지 상담에서 확인하고 싶습니다.\""
        )
    elif intent == "evidence_pack_explanation":
        answer = (
            "BADA Pack은 사용자님이 업로드한 증거를 정리해 상담 전 준비자료로 만드는 서비스입니다. "
            "급여명세서, 입금내역, 계약서, 대화 캡처, 모국어 메모 등 핵심 자료를 정리하고, 상담기관에서 확인할 수 있도록 요약합니다. "
            "최종 판단은 고용노동부나 전문가 상담을 통해 확인해야 합니다."
        )
    elif intent == "preparation_guidance":
        answer = (
            f"{summary} "
            "현재 자료로는 추가 준비가 필요한 항목이 있을 수 있으므로, 상담기관에서 더 정확히 확인해야 합니다. "
            "BADA는 신고 전 자료 정리 서비스입니다."
        )
    elif intent == "missing_document_check":
        if missing_docs:
            answer = (
                "현재 준비된 자료를 기준으로 다음 누락 자료가 확인됩니다: "
                + ", ".join(missing_docs)
                + "입니다. 이 자료를 추가로 준비하면 상담 전에 보다 명확하게 정리할 수 있습니다. "
                "최종 판단은 전문가 상담을 통해 확인해야 합니다."
            )
        else:
            answer = (
                "현재 자료로는 추가 누락 자료를 추정하기 어렵습니다. 상담기관에 가지고 가기 전에 제출 가능한 모든 관련 자료를 정리해 두세요. "
                "BADA는 신고 전 자료 정리 서비스입니다."
            )
    else:
        if difference is not None:
            answer = (
                f"현재 자료 기준으로 { _format_amount(difference) } 차이가 확인됩니다. "
                "이 차이는 상담기관에서 추가 확인이 필요합니다. "
                "BADA는 신고 전 자료 정리 서비스이며, 최종 판단은 전문가 상담에서 확인해야 합니다."
            )
        else:
            answer = (
                "제공된 메시지를 바탕으로 상담 전 준비자료와 다음 단계를 안내합니다. "
                "BADA는 신고 전 자료 정리 서비스입니다. 최종 판단은 고용노동부 또는 전문가 상담을 통해 확인해 주세요."
            )

    return answer, next_actions
