"""OCR 출력 검증 스키마 (worker 측).

LLM/Upstage 출력은 형식이 들쭉날쭉하므로 관대하게 받는다(추출 성공률↑):
- 금액/시급: null 허용 + "186,300원"·"1,795,680" 같은 문자열도 정수로 자동 변환
- hours: 문자열·null 흡수
값이 없으면 None으로 둔다 → 검증 실패로 통째 버려지는 일을 막는다.

주의: `from __future__ import annotations` 를 쓰지 않는다(중첩 모델 포워드 참조 즉시 해석 위해).
"""
import re
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Confidence = Literal["high", "medium", "low"]


def _to_int(v):
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(round(v))
    if isinstance(v, str):
        s = re.sub(r"[^\d-]", "", v)
        return int(s) if s and s not in ("-", "") else None
    return None


def _to_float(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = re.sub(r"[^\d.]", "", v)
        try:
            return float(s) if s else None
        except ValueError:
            return None
    return None


def _to_bool(v):
    """'예/유/있음/서명함/true' → True, '아니오/무/없음/false' → False, 그 외 None."""
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "yes", "y", "예", "유", "있음", "서명", "서명함", "o", "1"):
        return True
    if s in ("false", "no", "n", "아니오", "아니요", "무", "없음", "미서명", "x", "0"):
        return False
    return None


class Amount(BaseModel):
    label: Optional[str] = None
    value: Optional[int] = None
    confidence: Confidence = "medium"

    @field_validator("value", mode="before")
    @classmethod
    def _v(cls, v):
        return _to_int(v)


class Deduction(BaseModel):
    name: Optional[str] = None
    amount: Optional[int] = None
    confidence: Confidence = "medium"

    @field_validator("amount", mode="before")
    @classmethod
    def _v(cls, v):
        return _to_int(v)


class Utterance(BaseModel):
    speaker: Optional[str] = None
    text: str = ""
    kind: Literal["wage_promise", "work_order", "underpayment_admit", "evasive", "other"] = "other"
    confidence: Confidence = "medium"

    @field_validator("kind", mode="before")
    @classmethod
    def _k(cls, v):
        allowed = {"wage_promise", "work_order", "underpayment_admit", "evasive", "other"}
        return v if v in allowed else "other"


class ExtractedEntities(BaseModel):
    dates: List[str] = Field(default_factory=list)
    amounts: List[Amount] = Field(default_factory=list)
    hourly_wage: Optional[int] = None
    monthly_wage: Optional[int] = None
    hours: List[float] = Field(default_factory=list)
    deductions: List[Deduction] = Field(default_factory=list)
    workplace_name: Optional[str] = None
    employer_name: Optional[str] = None
    pay_date: Optional[str] = None
    utterances: List[Utterance] = Field(default_factory=list)

    # --- 확장 필드(판정 정확도용). 없으면 None/0 으로 둔다. ---
    work_days: Optional[int] = None             # 근무일수
    overtime_hours: Optional[float] = None       # 연장근로(1.5배 대상) 시간
    night_hours: Optional[float] = None          # 야간근로(22~06시, +0.5배) 시간
    holiday_hours: Optional[float] = None        # 휴일근로(1.5배 대상) 시간
    contract_start: Optional[str] = None         # 계약 시작일
    contract_end: Optional[str] = None           # 계약 종료일
    signed: Optional[bool] = None                # 서명·날인 유무

    @field_validator("hourly_wage", "monthly_wage", "work_days", mode="before")
    @classmethod
    def _i(cls, v):
        return _to_int(v)

    @field_validator("overtime_hours", "night_hours", "holiday_hours", mode="before")
    @classmethod
    def _f(cls, v):
        return _to_float(v)

    @field_validator("signed", mode="before")
    @classmethod
    def _b(cls, v):
        return _to_bool(v)

    @field_validator("workplace_name", "employer_name", "pay_date",
                     "contract_start", "contract_end", mode="before")
    @classmethod
    def _s(cls, v):
        """모델이 {value:..}/{promised:..} 객체로 줄 때 대표 문자열만 뽑는다(검증 실패 방지)."""
        if v is None or isinstance(v, str):
            return v
        if isinstance(v, dict):
            for k in ("value", "promised", "date", "text", "name"):
                if isinstance(v.get(k), str):
                    return v[k]
            return None
        return str(v)

    @field_validator("hours", mode="before")
    @classmethod
    def _h(cls, v):
        if not isinstance(v, list):
            return []
        return [x for x in (_to_float(i) for i in v) if x is not None]

    @field_validator("dates", mode="before")
    @classmethod
    def _d(cls, v):
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if x]


class OcrResult(BaseModel):
    raw_text: str = ""
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
