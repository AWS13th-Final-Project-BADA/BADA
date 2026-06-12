from app.config import settings
from app.schemas_ai_chat import ChatMessageRequest
from app.services.ai_chat_orchestrator import run_chat


def test_ai_chat_mock_safe(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=1,
            message="고용노동부에 가기 전에 뭘 준비해야 하나요?",
            language="ko",
        )
    )

    assert result["intent"] == "preparation_guidance"
    assert result["risk_level"] == "safe"
    assert result["ai_provider"] == "mock"
    assert result["used_case_context"] is True
    assert result["used_rag"] is False
    assert result["fallback_used"] is False
    assert result["sources"] == []
    assert result["next_actions"]


def test_ai_chat_blocks_korean_legal_judgment(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=1,
            message="이거 불법인가요? 체불임금 확정인가요?",
            language="ko",
        )
    )

    assert result["intent"] == "legal_judgment_risk"
    assert result["risk_level"] == "blocked"
    assert result["ai_provider"] == "blocked_fallback"
    assert result["fallback_used"] is True
    assert "법률 판단" in result["answer"]


def test_ai_chat_blocks_english_legal_judgment(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=1,
            message="Is this illegal? Should I sue the employer immediately?",
            language="auto",
        )
    )

    assert result["intent"] == "legal_judgment_risk"
    assert result["risk_level"] == "blocked"
    assert result["ai_provider"] == "blocked_fallback"
    assert "legal judgment" in result["answer"]


def test_ai_chat_blocks_vietnamese_legal_judgment(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=1,
            message="Điều này có bất hợp pháp không? Tôi có nên kiện ngay không?",
            language="auto",
        )
    )

    assert result["intent"] == "legal_judgment_risk"
    assert result["risk_level"] == "blocked"
    assert result["ai_provider"] == "blocked_fallback"
    assert "đánh giá pháp lý" in result["answer"]


def test_ai_chat_bedrock_failure_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "bedrock")

    def fail_llm(**kwargs):
        raise RuntimeError("no credentials")

    monkeypatch.setattr("app.services.ai_chat_orchestrator.generate_llm_chat_answer", fail_llm)

    result = run_chat(
        ChatMessageRequest(
            case_id=1,
            message="자료가 충분한지 확인해 주세요.",
            language="ko",
        )
    )

    assert result["intent"] == "missing_document_check"
    assert result["risk_level"] == "review"
    assert result["ai_provider"] == "bedrock_fallback"
    assert result["guardrail_result"] == "passed"
    assert result["answer"]
