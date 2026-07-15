from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class RagSource(BaseModel):
    source_id: str
    title: str
    source_org: str
    section: Optional[str] = None
    excerpt: Optional[str] = None
    retrieval_method: Optional[str] = None


class ChatMessageRequest(BaseModel):
    session_id: Optional[int] = None
    # 사건 UUID 문자열. 모바일/웹 모두 사건 ID(UUID)를 보낸다. 미지정(None)이면 일반 상담.
    case_id: Optional[str] = Field(default=None, example="550e8400-e29b-41d4-a716-446655440000")
    message: str = Field(..., example="고용노동부에 가기 전에 뭘 준비해야 하나요?")
    language: str = Field(default="auto", example="auto")


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
