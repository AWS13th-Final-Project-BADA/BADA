from app.config import settings
from app.schemas_ai_chat import ChatMessageRequest
from app.services.ai_chat_orchestrator import run_chat
from app.services.rag_retriever import RetrievedChunk


def test_ai_chat_mock_safe(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=None,
            message="고용노동부에 가기 전에 뭘 준비해야 하나요?",
            language="ko",
        )
    )

    assert result["intent"] == "preparation_guidance"
    assert result["risk_level"] == "safe"
    assert result["ai_provider"] == "mock"
    assert result["used_case_context"] is False
    assert result["used_rag"] is False
    assert result["fallback_used"] is False
    assert result["sources"] == []
    assert result["next_actions"]


def test_ai_chat_blocks_korean_legal_judgment(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=None,
            message="이거 불법인가요? 체불임금 확정인가요?",
            language="ko",
        )
    )

    assert result["intent"] == "legal_judgment_risk"
    assert result["risk_level"] == "blocked"
    assert result["ai_provider"] == "blocked_fallback"
    assert result["fallback_used"] is True
    assert "걱정되거나 억울하게" in result["answer"]


def test_ai_chat_blocks_english_legal_judgment(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=None,
            message="Is this illegal? Should I sue the employer immediately?",
            language="auto",
        )
    )

    assert result["intent"] == "legal_judgment_risk"
    assert result["risk_level"] == "blocked"
    assert result["ai_provider"] == "blocked_fallback"
    assert "understand" in result["answer"].lower()


def test_ai_chat_blocks_vietnamese_legal_judgment(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")

    result = run_chat(
        ChatMessageRequest(
            case_id=None,
            message="Điều này có bất hợp pháp không? Tôi có nên kiện ngay không?",
            language="auto",
        )
    )

    assert result["intent"] == "legal_judgment_risk"
    assert result["risk_level"] == "blocked"
    assert result["ai_provider"] == "blocked_fallback"
    assert "Tôi hiểu" in result["answer"]


def test_ai_chat_bedrock_failure_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "bedrock")

    def fail_llm(**kwargs):
        raise RuntimeError("no credentials")

    monkeypatch.setattr("app.services.ai_chat_orchestrator.generate_llm_chat_answer", fail_llm)

    result = run_chat(
        ChatMessageRequest(
            case_id=None,
            message="자료가 충분한지 확인해 주세요.",
            language="ko",
        )
    )

    assert result["intent"] == "missing_document_check"
    assert result["risk_level"] == "review"
    assert result["ai_provider"] == "bedrock_fallback"
    assert result["guardrail_result"] == "passed"
    assert result["answer"]

def test_ai_chat_returns_clickable_rag_source_details(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_mode", "mock")
    chunk = RetrievedChunk(
        source_id="molab-consultation-guide",
        title="고용노동부 상담 준비자료",
        source_org="고용노동부",
        section="임금 자료",
        text="급여명세서와 계좌 입금내역을 같은 기간끼리 정리해 상담 시 함께 제시합니다.",
        score=12.0,
        retrieval_method="keyword",
    )
    monkeypatch.setattr(
        "app.services.ai_chat_orchestrator.retrieve_rag_context",
        lambda **kwargs: [chunk],
    )

    result = run_chat(
        ChatMessageRequest(
            case_id=None,
            message="노동청 상담 전에 어떤 자료를 준비해야 하나요?",
            language="ko",
        )
    )

    assert result["used_rag"] is True
    assert result["sources"][0]["source_id"] == chunk.source_id
    assert result["sources"][0]["excerpt"] == chunk.text
    assert result["sources"][0]["retrieval_method"] == "keyword"
