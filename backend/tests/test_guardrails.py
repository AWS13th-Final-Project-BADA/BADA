from app.services.guardrail_service import apply_output_guardrail, contains_forbidden_text
from app.services.legal_risk_classifier import classify_legal_risk


def test_input_guardrail_blocks_ko_en_vi_legal_judgment_questions():
    examples = [
        "이거 불법인가요? 바로 신고해도 되나요?",
        "Is this illegal? Should I sue them?",
        "Điều này có bất hợp pháp không? Có nên kiện ngay không?",
    ]

    for message in examples:
        risk_level, blocked = classify_legal_risk(message)
        assert risk_level == "blocked"
        assert blocked is True


def test_input_guardrail_marks_preparation_questions_as_review_or_safe():
    examples = [
        "진정서에는 어떤 내용을 적어야 하나요?",
        "What should I prepare before consultation?",
        "Đơn khiếu nại thường cần viết những nội dung gì?",
    ]

    for message in examples:
        risk_level, blocked = classify_legal_risk(message)
        assert risk_level in {"safe", "review"}
        assert blocked is False


def test_output_guardrail_blocks_forbidden_ko_en_vi_conclusions():
    examples = [
        "이 사안은 불법입니다. 바로 신고하세요.",
        "This is illegal. You will definitely receive the money.",
        "Đây là bất hợp pháp. Bạn chắc chắn sẽ nhận được tiền.",
    ]

    for answer in examples:
        assert contains_forbidden_text(answer)


def test_output_guardrail_returns_localized_fallback():
    answer, result, fallback_used = apply_output_guardrail(
        "Đây là bất hợp pháp. Hãy kiện ngay.",
        "vi",
    )

    assert result == "failed"
    assert fallback_used is True
    assert "Tôi hiểu" in answer


def test_output_guardrail_returns_empathetic_localized_fallbacks():
    examples = [
        ("This is illegal. You will definitely receive the money.", "en", "understand"),
        ("이 사안은 불법입니다. 바로 신고하세요.", "ko", "걱정되거나 억울하게"),
        ("Đây là bất hợp pháp. Hãy kiện ngay.", "vi", "Tôi hiểu"),
    ]

    for answer, language, expected in examples:
        fallback, result, fallback_used = apply_output_guardrail(answer, language)
        assert result == "failed"
        assert fallback_used is True
        assert expected in fallback
