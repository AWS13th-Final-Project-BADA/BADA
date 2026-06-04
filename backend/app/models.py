"""SQLAlchemy ORM 모델 — domain.md 스키마와 1:1.

DB 테이블 정의만 둔다. 비즈니스 계산은 worker/rules 에서 한다(architecture.md).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str | None] = mapped_column(String(100))
    preferred_lang: Mapped[str] = mapped_column(String(10), default="ko")  # ko/vi/km/ne/id/en
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    workplace_name: Mapped[str | None] = mapped_column(String(200))
    employer_name: Mapped[str | None] = mapped_column(String(100))
    work_start_date: Mapped[date | None] = mapped_column(Date)
    work_end_date: Mapped[date | None] = mapped_column(Date)  # NULL = 진행중
    agreed_hourly_wage: Mapped[int | None] = mapped_column(Integer)  # 원
    agreed_weekly_hours: Mapped[float | None] = mapped_column(Numeric(4, 1))
    issue_types: Mapped[list | None] = mapped_column(JSON)  # ["wage_unpaid", ...]
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/analyzing/completed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    evidences: Mapped[list[Evidence]] = relationship(back_populates="case")


class Evidence(Base):
    __tablename__ = "evidences"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    file_key: Mapped[str] = mapped_column(String(500))  # S3 key
    file_name: Mapped[str | None] = mapped_column(String(300))
    file_type: Mapped[str] = mapped_column(String(50))  # image/pdf/text
    category: Mapped[str] = mapped_column(String(50))  # contract/schedule/payment/chat/statement/other
    upload_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ocr_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/processing/done/failed
    ocr_text: Mapped[str | None] = mapped_column(Text)
    extracted_entities: Mapped[dict | None] = mapped_column(JSON)

    case: Mapped[Case] = relationship(back_populates="evidences")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    event_date: Mapped[date | None] = mapped_column(Date)  # NULL 가능(추정불가)
    event_type: Mapped[str] = mapped_column(String(50))  # work_start/wage_promise/payment/underpayment/chat/gps
    description: Mapped[str | None] = mapped_column(Text)  # 한국어
    description_translated: Mapped[str | None] = mapped_column(Text)  # 모국어
    source_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidences.id"))
    confidence: Mapped[str] = mapped_column(String(10), default="medium")  # high/medium/low
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TranslationPair(Base):
    __tablename__ = "translation_pairs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str | None] = mapped_column(String(50))
    related_issue: Mapped[str | None] = mapped_column(String(100))
    source_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidences.id"))


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    total_expected_wage: Mapped[int | None] = mapped_column(Integer)
    total_received_wage: Mapped[int | None] = mapped_column(Integer)
    suspected_unpaid: Mapped[int | None] = mapped_column(Integer)
    deduction_items: Mapped[list | None] = mapped_column(JSON)
    calculation_detail: Mapped[dict | None] = mapped_column(JSON)
    timeline_summary: Mapped[str | None] = mapped_column(Text)
    missing_evidences: Mapped[list | None] = mapped_column(JSON)
    pdf_ko_s3_key: Mapped[str | None] = mapped_column(String(500))
    pdf_native_s3_key: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Workplace(Base):
    """지오펜스 — MVP는 중심점+반경(원). 폴리곤은 Phase 2."""
    __tablename__ = "workplaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    center_lat: Mapped[float] = mapped_column(Numeric(10, 7))
    center_lng: Mapped[float] = mapped_column(Numeric(10, 7))
    radius_m: Mapped[int] = mapped_column(Integer, default=50)


class GpsLog(Base):
    __tablename__ = "gps_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    ts: Mapped[datetime] = mapped_column(DateTime)
    lat: Mapped[float] = mapped_column(Numeric(10, 7))
    lng: Mapped[float] = mapped_column(Numeric(10, 7))
    status: Mapped[str | None] = mapped_column(String(20))  # IN_WORKPLACE/OUTSIDE
    is_mocked: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="seed")  # web_geo/seed/app
