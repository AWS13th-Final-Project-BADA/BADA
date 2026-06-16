from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..config import settings
from .language_service import language_name, normalize_language_code

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are BADA Connect, a consultation-preparation assistant for migrant workers in Korea.

Hard rules:
- Do not make legal judgments.
- Do not say that an employer violated the law.
- Do not say that unpaid wages, illegality, or a receivable amount is confirmed.
- Do not tell the user to sue, report immediately, or guarantee a result.
- Explain only what can be organized before a consultation.
- Use the provided case context only as preparation material.
- Use retrieved reference context only to explain preparation steps, missing documents, and source-backed guidance.
- If reference context is provided, do not invent source names or claims outside it.
- If a question needs legal judgment, say that the final judgment must be confirmed by the Ministry of Employment and Labor, a counseling center, or a qualified expert.
- Answer in the requested output language only. Keep official source titles or organization names in their original language if needed, but explain them in the requested output language.
- For Vietnamese answers, when Korean official terms appear, include a short Vietnamese explanation in parentheses, e.g. 급여명세서(bảng lương), 입금내역(lịch sử chuyển khoản), 근로계약서(hợp đồng lao động), 고용노동부(Bộ Việc làm và Lao động).

Return only valid JSON with this shape:
{
  "answer": "short, helpful answer in the requested language",
  "next_actions": ["concrete preparation action", "concrete preparation action"]
}
Return compact JSON only on a single line. Do not use markdown.
Keep "answer" under 120 words.
Include 2 or 3 next_actions.
Keep each next_actions item under 20 words.
"""


def generate_llm_chat_answer(
    *,
    intent: str,
    risk_level: str,
    case_context: dict[str, Any] | None,
    rag_context: str,
    message: str,
    language: str,
) -> tuple[str, list[str]]:
    if settings.ai_chat_mode.lower() == "bedrock":
        return _generate_with_bedrock(
            intent=intent,
            risk_level=risk_level,
            case_context=case_context,
            rag_context=rag_context,
            message=message,
            language=language,
        )

    raise RuntimeError(f"Unsupported AI_CHAT_MODE for LLM service: {settings.ai_chat_mode}")


def _generate_with_bedrock(
    *,
    intent: str,
    risk_level: str,
    case_context: dict[str, Any] | None,
    rag_context: str,
    message: str,
    language: str,
) -> tuple[str, list[str]]:
    try:
        import boto3  # Lazy import so mock mode does not require AWS SDK.
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
        "max_tokens": max(settings.ai_chat_max_tokens, 1200),
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
                            rag_context=rag_context,
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
    rag_context: str,
    message: str,
    language: str,
) -> str:
    output_language = normalize_language_code(language)
    output_language_name = language_name(output_language)
    context_text = json.dumps(case_context or {}, ensure_ascii=False, indent=2)
    return f"""Requested output language code: {output_language}
Requested output language name: {output_language_name}
Intent: {intent}
Risk level: {risk_level}
User question: {message}

Case context:
{context_text}

Retrieved reference context:
{rag_context}

Write a concise preparation-focused answer.
The answer and every next_actions item MUST be written in {output_language_name}.
Do not switch to Korean unless the requested output language is Korean.
If the retrieved reference context is Korean, translate or summarize the useful guidance into {output_language_name}.
For Vietnamese, keep important Korean official terms and add Vietnamese parentheses for them.
Return compact single-line JSON only.
Include 2 or 3 practical next_actions.
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
            parsed = _parse_partial_json_text(text)
        else:
            try:
                parsed = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                parsed = _parse_partial_json_text(text)

    answer = str(parsed.get("answer") or "").strip()
    if not answer:
        raise RuntimeError("LLM response did not include answer")

    raw_next_actions = parsed.get("next_actions") or []
    next_actions = [str(item).strip() for item in raw_next_actions if str(item).strip()]
    if not next_actions and case_context:
        next_actions = case_context.get("next_actions", [])

    logger.info("Generated AI chat answer with provider=bedrock")
    return answer, next_actions


def _parse_partial_json_text(text: str) -> dict[str, Any]:
    """Recover usable fields from a truncated model JSON response."""
    answer = _extract_json_string_field(text, "answer")
    if not answer:
        raise json.JSONDecodeError("LLM response did not contain a complete answer field", text, 0)

    actions: list[str] = []
    array_match = re.search(r'"next_actions"\s*:\s*\[(.*)', text, flags=re.DOTALL)
    if array_match:
        for item in re.finditer(r'"((?:\\.|[^"\\])*)"', array_match.group(1)):
            try:
                actions.append(json.loads(f'"{item.group(1)}"'))
            except json.JSONDecodeError:
                continue

    return {"answer": answer, "next_actions": actions}


def _extract_json_string_field(text: str, field_name: str) -> str:
    match = re.search(rf'"{re.escape(field_name)}"\s*:\s*"', text)
    if not match:
        return ""

    chars: list[str] = []
    escaped = False
    for char in text[match.end() :]:
        if escaped:
            chars.append("\\" + char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            raw = "".join(chars)
            try:
                return json.loads(f'"{raw}"').strip()
            except json.JSONDecodeError:
                return raw.strip()
        chars.append(char)
    return ""
