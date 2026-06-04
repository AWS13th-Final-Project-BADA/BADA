"""OCR 출력 검증 스키마 (worker 측). backend/app/schemas.py:OcrResult 와 동일 형태.

LLM/Upstage 출력을 이 스키마로 강제 검증한다(architecture.md). 실패 시 재시도.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class Amount(BaseModel):
    label: Optional[str] = None
    value: int
    confidence: Confidence = "medium"


class Deduction(BaseModel):
    name: str
    amount: int
    confidence: Confidence = "medium"


class Utterance(BaseModel):
    speaker: Optional[str] = None
    text: str
    kind: Literal["wage_promise", "work_order", "underpayment_admit", "evasive", "other"] = "other"
    confidence: Confidence = "medium"


class ExtractedEntities(BaseModel):
    dates: list[str] = Field(default_factory=list)
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
    raw_text: str = ""
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
