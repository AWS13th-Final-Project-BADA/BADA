"""표준 분석 응답 계약(AnalysisReport) — 다른 기능·서비스가 안정적으로 연동하는 단일 스키마.

설계 원칙(연동 친화):
  - schema_version 으로 계약 버전 고정.
  - enum 으로 상태/심각도/신뢰도/판정유형을 못 박음(임의 문자열 금지).
  - 금액은 정수 + currency 명시. 모르면 None(=확인 불가). 0과 구분.
  - 기계용 구조화 데이터와 사람용 문장(narrative)을 분리.
  - /analyze 와 /analysis 가 '완전히 동일한' 모양을 반환.

FastAPI response_model 로 쓰면 /docs(OpenAPI)가 자동 생성된다.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class CompareStatus(str, Enum):
    match = "match"
    mismatch = "mismatch"
    missing = "missing"


class Severity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class FindingType(str, Enum):
    minimum_wage = "minimum_wage"            # 계약/약속 시급이 최저임금 미달
    minimum_wage_paid = "minimum_wage_paid"  # 실지급 기준 시급이 최저임금 미달
    premium_pay = "premium_pay"              # 연장/야간/휴일 가산수당 점검
    insurance_over = "insurance_over"         # 4대보험 과다공제 의심


class Period(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None  # None = 진행중/미상


class CaseInfo(BaseModel):
    id: str
    workplace: Optional[str] = None
    employer: Optional[str] = None
    period: Period = Field(default_factory=Period)
    issue_types: list[str] = Field(default_factory=list)


class Wage(BaseModel):
    currency: str = "KRW"
    computable: bool = False                  # 차액을 계산할 수 있었는지
    agreed_hourly: Optional[int] = None
    expected: Optional[int] = None            # 기대 급여
    received: Optional[int] = None            # 실수령(입금 없으면 None — '0원' 단정 금지)
    suspected_unpaid: Optional[int] = None    # 미지급 의심(확정 아님)
    basis: Optional[str] = None               # 산식 설명
    notes: list[str] = Field(default_factory=list)


class Deduction(BaseModel):
    name: str
    category: str
    amount: int
    currency: str = "KRW"
    sources: list[str] = Field(default_factory=list)  # 어느 자료에서 확인됐는지
    verify: str = ""                                   # 확인 필요 안내


class Comparison(BaseModel):
    key: str
    label: str
    status: CompareStatus
    values: dict = Field(default_factory=dict)
    note: Optional[str] = None


class MinWage(BaseModel):
    year: int
    hourly: int


class Finding(BaseModel):
    type: FindingType
    severity: Severity
    message: str
    amount: Optional[int] = None


class Legal(BaseModel):
    min_wage: MinWage
    findings: list[Finding] = Field(default_factory=list)


class TimelineItem(BaseModel):
    date: Optional[str] = None
    type: str
    text: str
    text_translated: Optional[str] = None
    source_evidence_id: Optional[str] = None
    confidence: Confidence = Confidence.medium


class TranslationItem(BaseModel):
    source_text: str
    translated_text: str
    evidence_type: Optional[str] = None
    related_issue: Optional[str] = None


class MissingItem(BaseModel):
    item: str
    reason: str


class Gps(BaseModel):
    tagged_count: int = 0
    cross_matches: int = 0


class Narrative(BaseModel):
    summary: str = ""
    disclaimer: str = ""


class Meta(BaseModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: Optional[str] = None
    lang: str = "ko"
    provider_mode: str = "local"


class AnalysisReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    case: CaseInfo
    wage: Wage
    deductions: list[Deduction] = Field(default_factory=list)
    comparisons: list[Comparison] = Field(default_factory=list)
    legal: Legal
    timeline: list[TimelineItem] = Field(default_factory=list)
    translations: list[TranslationItem] = Field(default_factory=list)
    missing: list[MissingItem] = Field(default_factory=list)
    gps: Optional[Gps] = None
    narrative: Narrative = Field(default_factory=Narrative)
    meta: Meta = Field(default_factory=Meta)
