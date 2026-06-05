from __future__ import annotations

import json
import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are BADA Connect, a consultation-preparation assistant for migrant workers in Korea.

Hard rules:
- Do not make legal judgments.
- Do not say that an employer violated the law.
- Do not say that unpaid wages, illegality, or a receivable amount is confirmed.
- Do not tell the user to sue, report immediately, or guarantee a result.
- Explain only what can be organized before a consultation.
- Use the provided case context only as preparation material.
- If a question needs legal judgment, say that the final judgment must be confirmed by the Ministry of Employment and Labor, a counseling center, or a qualified expert.

Return only valid JSON with this shape:
{
  "answer": "short, helpful answer in the requested language",
  "next_actions": ["concrete preparation action", "concrete preparation action"]
}
"""


def generate_llm_chat_answer(
    *,
    intent: str,
    risk_level: str,
    case_context: dict[str, Any] | None,
    message: str,
    language: str,
) -> tuple[str, list[str]]:
    if settings.ai_chat_mode.lower() == "bedrock":
        return _generate_with_bedrock(
            intent=intent,
            risk_level=risk_level,
            case_context=case_context,
            message=message,
            language=language,
        )

    raise RuntimeError(f"Unsupported AI_CHAT_MODE for LLM service: {settings.ai_chat_mode}")


def _generate_with_bedrock(
    *,
    intent: str,
    risk_level: str,
    case_context: dict[str, Any] | None,
    message: str,
    language: str,
) -> tuple[str, list[str]]:
    try:
        import boto3  # 지연 임포트: mock 모드에서는 AWS SDK가 필요 없다.
    except ImportError as exc:
        raise RuntimeError("boto3 is required for AI_CHAT_MODE=bedrock") from exc

    session = (
        boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
        if settings.aws_profile
        else boto3.Session(region_name=settings.aws_region)
    )
    client = session.client("bedrock-runtime")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": settings.ai_chat_max_tokens,
        "temperature": 0.2,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_user_prompt(
                            intent=intent,
                            risk_level=risk_level,
                            case_context=case_context,
                            message=message,
                            language=language,
                        ),
                    }
                ],
            }
        ],
    }

    response = client.invoke_model(
        modelId=settings.bedrock_model_id,
        body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    raw_body = response["body"].read().decode("utf-8")
    raw = json.loads(raw_body)
    text = _extract_bedrock_text(raw)
    return _parse_llm_json(text, case_context)


def _build_user_prompt(
    *,
    intent: str,
    risk_level: str,
    case_context: dict[str, Any] | None,
    message: str,
    language: str,
) -> str:
    context_text = json.dumps(case_context or {}, ensure_ascii=False, indent=2)
    return f"""Requested language: {language}
Intent: {intent}
Risk level: {risk_level}
User question: {message}

Case context:
{context_text}

Write a concise preparation-focused answer. Include practical next_actions.
"""


def _extract_bedrock_text(raw: dict[str, Any]) -> str:
    content = raw.get("content", [])
    text_parts = [
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    text = "\n".join(part for part in text_parts if part).strip()
    if not text:
        raise RuntimeError("Bedrock response did not contain text content")
    return text


def _parse_llm_json(text: str, case_context: dict[str, Any] | None) -> tuple[str, list[str]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])

    answer = str(parsed.get("answer") or "").strip()
    if not answer:
        raise RuntimeError("LLM response did not include answer")

    raw_next_actions = parsed.get("next_actions") or []
    next_actions = [str(item).strip() for item in raw_next_actions if str(item).strip()]
    if not next_actions and case_context:
        next_actions = case_context.get("next_actions", [])

    logger.info("Generated AI chat answer with provider=bedrock")
    return answer, next_actions
