from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from .case_context_service import load_case_context
from .guardrail_service import apply_output_guardrail, build_disclaimer
from .intent_classifier import classify_intent
from .legal_risk_classifier import classify_legal_risk
from .llm_service import generate_llm_chat_answer
from .mock_llm_service import generate_chat_answer, generate_legal_judgment_fallback
from .rag_retriever import RetrievedChunk, format_rag_context, retrieve_rag_context

logger = logging.getLogger(__name__)


def run_chat(payload: Any, db: Session | None = None) -> dict[str, Any]:
    intent = classify_intent(payload.message)
    risk_level, _ = classify_legal_risk(payload.message)
    case_context = load_case_context(payload.case_id)
    used_case_context = case_context is not None
    rag_chunks: list[RetrievedChunk] = []

    if risk_level == "blocked":
        answer, next_actions = generate_legal_judgment_fallback(case_context)
        guardrail_result = "passed"
        fallback_used = True
        ai_provider = "blocked_fallback"
    else:
        rag_chunks = retrieve_rag_context(
            db=db,
            question=payload.message,
            intent=intent,
            language=payload.language,
        )
        answer, next_actions, ai_provider = _generate_answer(
            intent=intent,
            risk_level=risk_level,
            case_context=case_context,
            rag_chunks=rag_chunks,
            message=payload.message,
            language=payload.language,
        )
        answer, guardrail_result, fallback_used = apply_output_guardrail(answer)

        if guardrail_result == "failed":
            answer, next_actions = generate_legal_judgment_fallback(case_context)
            fallback_used = True
            ai_provider = f"{ai_provider}_guardrail_fallback"

    return {
        "answer": answer,
        "intent": intent,
        "risk_level": risk_level,
        "ai_provider": ai_provider,
        "used_case_context": used_case_context,
        "used_rag": bool(rag_chunks),
        "guardrail_result": guardrail_result,
        "fallback_used": fallback_used,
        "sources": _dedupe_sources(rag_chunks),
        "next_actions": next_actions,
        "disclaimer": build_disclaimer(),
    }


def _generate_answer(
    *,
    intent: str,
    risk_level: str,
    case_context: dict[str, Any] | None,
    rag_chunks: list[RetrievedChunk],
    message: str,
    language: str,
) -> tuple[str, list[str], str]:
    mode = settings.ai_chat_mode.lower().strip()
    if mode == "mock":
        answer, next_actions = generate_chat_answer(intent, case_context, message, language)
        return answer, next_actions, "mock"

    if mode == "bedrock":
        try:
            answer, next_actions = generate_llm_chat_answer(
                intent=intent,
                risk_level=risk_level,
                case_context=case_context,
                rag_context=format_rag_context(rag_chunks),
                message=message,
                language=language,
            )
            return answer, next_actions, "bedrock"
        except Exception as exc:
            logger.warning("AI chat LLM generation failed; falling back to mock: %s", exc)
            answer, next_actions = generate_chat_answer(intent, case_context, message, language)
            return answer, next_actions, "bedrock_fallback"

    logger.warning("Unknown AI_CHAT_MODE=%s; falling back to mock", settings.ai_chat_mode)
    answer, next_actions = generate_chat_answer(intent, case_context, message, language)
    return answer, next_actions, "mock"


def _dedupe_sources(chunks: list[RetrievedChunk]) -> list[dict[str, str | None]]:
    sources: list[dict[str, str | None]] = []
    seen: set[tuple[str, str | None]] = set()
    for chunk in chunks:
        key = (chunk.source_id, chunk.section)
        if key in seen:
            continue
        seen.add(key)
        sources.append(chunk.to_source())
    return sources
