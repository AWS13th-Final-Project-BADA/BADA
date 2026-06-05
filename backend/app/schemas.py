"""Pydantic 스키마 — API 입출력 + LLM 출력 강제.

LLM 추출 결과는 반드시 이 스키마로 검증한다(architecture.md). 검증 실패 → 재시도.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Lang = Literal["ko", "vi", "km", "ne", "id", "en", "th", "ja"]
Category = Literal["contract", "schedule", "payment", "chat", "statement", "other"]
Confidence = Literal["high", "medium", "low"]


# ---------- API: 사건 ----------
class CaseCreate(BaseModel):
    workplace_name: Optional[str] = None
    employer_name: Optional[str] = None
    work_start_date: Optional[date] = None
    work_end_date: Optional[date] = None
    agreed_hourly_wage: Optional[int] = None
    agreed_weekly_hours: Optional[float] = None
    issue_types: list[str] = Field(default_factory=list)


class PresignedUploadRequest(BaseModel):
    file_name: str
    file_type: Literal["image", "pdf", "text"]
    category: Category


# ---------- LLM 출력 스키마 (검증 강제) ----------
class Amount(BaseModel):
    label: Optional[str] = None      # 예: "지급액", "기숙사비"
    value: int                        # 원 단위 정수 (LLM이 콤마 제거해 반환)
    confidence: Confidence = "medium"


class Deduction(BaseModel):
    name: str                         # 원문 표기 (정규화는 규칙엔진이)
    amount: int
    confidence: Confidence = "medium"


class Utterance(BaseModel):
    speaker: Optional[str] = None     # 사업주/근로자/불명
    text: str
    kind: Literal["wage_promise", "work_order", "underpayment_admit", "evasive", "other"]
    confidence: Confidence = "medium"


class ExtractedEntities(BaseModel):
    """이미지 1건에서 뽑은 엔티티. Vision/Upstage 출력은 이 스키마로 강제."""
    dates: list[str] = Field(default_factory=list)        # ISO 또는 원문
    amounts: list[Amount] = Field(default_factory=list)
    hourly_wage: Optional[int] = None
    monthly_wage: Optional[int] = None
    hours: list[float] = Field(default_factory=list)
    deductions: list[Deduction] = Field(default_factory=list)
    workplace_name: Optional[str] = None
    employer_name: Optional[str] = None
    pay_date: Optional[str] = None
    utterances: list[Utterance] = Field(default_factory=list)


class OcrResult(BaseModel):
    raw_text: str
    entities: ExtractedEntities
