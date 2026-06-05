from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class RagSource(BaseModel):
    source_id: str
    title: str
    source_org: str
    section: Optional[str] = None


class ChatMessageRequest(BaseModel):
    session_id: Optional[int] = None
    case_id: int = Field(..., example=1)
    message: str = Field(..., example="고용노동부 가기 전에 뭘 준비해야 하나요?")
    language: str = Field(default="ko", example="ko")


class ChatMessageResponse(BaseModel):
    answer: str
    intent: str
    risk_level: str
    ai_provider: str
    used_case_context: bool
    used_rag: bool
    guardrail_result: str
    fallback_used: bool
    sources: List[RagSource] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    disclaimer: str
