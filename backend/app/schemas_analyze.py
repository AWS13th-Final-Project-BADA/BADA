"""분석 요청 스키마. OCR이 스텁이므로, 추출됐다고 가정한 값을 직접 받는다(W2에 Bedrock으로 대체)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DepositItem(BaseModel):
    date: Optional[str] = None   # ISO 날짜(타임라인용, 선택)
    amount: int


class DeductionInput(BaseModel):
    name: str
    amount: int


class GpsPing(BaseModel):
    ts: str                      # ISO datetime
    lat: float
    lng: float
    is_mocked: bool = False


class WorkplaceGeo(BaseModel):
    lat: float
    lng: float
    radius_m: int = 50


class AnalyzeRequest(BaseModel):
    agreed_hourly_wage: Optional[int] = None   # 사용자가 수정한 시급(추출값 override)
    worked_hours: list[float] = Field(default_factory=list)
    deposits: list[DepositItem] = Field(default_factory=list)
    deductions: list[DeductionInput] = Field(default_factory=list)
    workplace: Optional[WorkplaceGeo] = None
    gps_logs: list[GpsPing] = Field(