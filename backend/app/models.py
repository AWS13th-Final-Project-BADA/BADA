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

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - local dev can run without pgvector installed.
    Vector = None


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)  # 소셜은 이메일 미동의 가능 → nullable
    name: Mapped[str | None] = mapped_column(String(100))
    preferred_lang: Mapped[str] = mapped_column(String(10), default="ko")  # ko/vi/km/ne/id/en
    # 소셜 로그인 식별자 (kakao/google/naver + 공급자측 고유 ID)
    provider: Mapped[str | None] = mapped_column(String(20))
    provider_id: Mapped[str | None] = mapped_column(String(100), index=True)
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
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)

    # ── 타임스탬프 (이중 검증) ──
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)       # 기기 시각
    server_ts: Mapped[datetime] = mapped_column(                                         # 서버 수신 시각
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_delayed_upload: Mapped[bool] = mapped_column(Boolean, default=False)             # |server_ts - ts| > 임계값

    # ── 좌표 ──
    lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    lng: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    altitude_m: Mapped[float | None] = mapped_column(Numeric(8, 2))
    speed_mps: Mapped[float | None] = mapped_column(Numeric(6, 3))                     # 이동 속도 이상 탐지

    # ── 측위 품질 ──
    accuracy_m: Mapped[float | None] = mapped_column(Numeric(7, 2))                    # GPS 오차 반경
    provider: Mapped[str | None] = mapped_column(String(20))                           # gps/network/fused

    # ── 모킹 탐지 ──
    is_mocked: Mapped[bool] = mapped_column(Boolean, default=False)
    mock_reason: Mapped[str | None] = mapped_column(String(50))                        # 판정 근거

    # ── 판정 결과 ──
    status: Mapped[str | None] = mapped_column(String(20))                             # IN_WORKPLACE/OUTSIDE

    # ── 무결성 체인 ──
    prev_chain_hash: Mapped[str | None] = mapped_column(String(64))                    # 직전 행 해시
    chain_hash: Mapped[str] = mapped_column(String(64), nullable=False)                # 현재 행 해시

    # ── 기기 식별 ──
    device_id: Mapped[str | None] = mapped_column(String(100))                         # 해시된 기기 ID
    device_os: Mapped[str | None] = mapped_column(String(30))
    app_version: Mapped[str | None] = mapped_column(String(20))

    # ── 데이터 출처 ──
    source: Mapped[str] = mapped_column(String(20), default="app")                     # app/web_geo/seed


class RagDocument(Base):
    __tablename__ = "rag_documents"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    source_org: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(10), default="ko")
    document_type: Mapped[str] = mapped_column(String(80), default="official_guide")
    version: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list[RagChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("rag_documents.id"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    keywords: Mapped[list | None] = mapped_column(JSON)
    embedding: Mapped[list | None] = mapped_column(Vector(1024) if Vector else JSON)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    document: Mapped[RagDocument] = relationship(back_populates="chunks")
