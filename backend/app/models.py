"""SQLAlchemy ORM models for BADA core data.

The schema keeps existing application attribute names stable while expanding the
database toward the production ERD. Evidence Pack JSON is the source of truth for
generated packs; PDF files are stored only as generated artifacts.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - local dev can run without pgvector installed.
    Vector = None


def _uuid() -> str:
    return str(uuid.uuid4())


def _json_type():
    return JSON().with_variant(JSONB, "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cognito_sub: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone_number: Mapped[str | None] = mapped_column(String(50))
    password_hash: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column("display_name", String(100))
    preferred_lang: Mapped[str] = mapped_column("preferred_language", String(10), default="ko", nullable=False, index=True)
    nationality: Mapped[str | None] = mapped_column(String(2))
    provider: Mapped[str | None] = mapped_column(String(20))
    provider_id: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    language_preferences: Mapped[list[UserLanguagePreference]] = relationship(back_populates="user", cascade="all, delete-orphan")
    cases: Mapped[list[Case]] = relationship(back_populates="user")


class UserLanguagePreference(Base):
    __tablename__ = "user_language_preferences"
    __table_args__ = (UniqueConstraint("user_id", "language_code", name="uq_user_language_preferences_user_language"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    can_read: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_speak: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="language_preferences")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Evidence Pack", nullable=False)
    issue_type: Mapped[str] = mapped_column(String(50), default="wage_difference", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    workplace_name: Mapped[str | None] = mapped_column(String(255))
    employer_name: Mapped[str | None] = mapped_column(String(255))
    work_start_date: Mapped[date | None] = mapped_column(Date)
    work_end_date: Mapped[date | None] = mapped_column(Date)
    agreed_hourly_wage: Mapped[int | None] = mapped_column(Integer)
    agreed_weekly_hours: Mapped[float | None] = mapped_column(Numeric(4, 1))
    issue_types: Mapped[list | None] = mapped_column(_json_type())
    primary_language: Mapped[str] = mapped_column(String(10), default="ko", nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="cases")
    evidences: Mapped[list[Evidence]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column("evidence_category", String(50), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str] = mapped_column("original_file_name", String(255), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    file_key: Mapped[str] = mapped_column("s3_key", Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    file_hash_sha256: Mapped[str | None] = mapped_column(String(64))
    language_hint: Mapped[str | None] = mapped_column(String(10))
    ocr_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    extraction_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", _json_type())
    ocr_text: Mapped[str | None] = mapped_column(Text)
    extracted_entities: Mapped[dict | None] = mapped_column(_json_type())
    upload_at: Mapped[datetime] = mapped_column("uploaded_at", DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    case: Mapped[Case] = relationship(back_populates="evidences")
    texts: Mapped[list[EvidenceText]] = relationship(back_populates="evidence", cascade="all, delete-orphan")
    extractions: Mapped[list[EvidenceExtraction]] = relationship(back_populates="evidence", cascade="all, delete-orphan")


class EvidenceText(Base):
    __tablename__ = "evidence_texts"
    __table_args__ = (UniqueConstraint("evidence_id", "text_type", "version", name="uq_evidence_texts_evidence_type_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True)
    text_type: Mapped[str] = mapped_column(String(30), nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(10))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    engine: Mapped[str | None] = mapped_column(String(50))
    engine_version: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evidence: Mapped[Evidence] = relationship(back_populates="texts")


class EvidenceExtraction(Base):
    __tablename__ = "evidence_extractions"
    __table_args__ = (UniqueConstraint("evidence_id", "extraction_type", "version", name="uq_evidence_extractions_evidence_type_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    extracted_json: Mapped[dict] = mapped_column(_json_type(), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evidence: Mapped[Evidence] = relationship(back_populates="extractions")


class CaseAnalysis(Base):
    __tablename__ = "case_analyses"
    __table_args__ = (
        UniqueConstraint("case_id", "analysis_version", name="uq_case_analyses_case_version"),
        CheckConstraint("readiness_score IS NULL OR (readiness_score >= 0 AND readiness_score <= 100)", name="ck_case_analyses_readiness_score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    expected_wage_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    actual_deposit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    difference_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="KRW", nullable=False)
    deduction_summary: Mapped[dict | None] = mapped_column(_json_type())
    calculation_details: Mapped[dict | None] = mapped_column(_json_type())
    missing_documents: Mapped[list | None] = mapped_column(_json_type())
    readiness_score: Mapped[int | None] = mapped_column(Integer)
    timeline_summary: Mapped[str | None] = mapped_column(Text)
    analysis_disclaimer: Mapped[str] = mapped_column(Text, default="This is consultation preparation, not legal judgment.", nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[str] = mapped_column(String(30), default="system", nullable=False)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    total_expected_wage: Mapped[int | None] = mapped_column(Integer)
    total_received_wage: Mapped[int | None] = mapped_column(Integer)
    suspected_unpaid: Mapped[int | None] = mapped_column(Integer)
    deduction_items: Mapped[list | None] = mapped_column(_json_type())
    calculation_detail: Mapped[dict | None] = mapped_column(_json_type())
    timeline_summary: Mapped[str | None] = mapped_column(Text)
    missing_evidences: Mapped[list | None] = mapped_column(_json_type())
    pdf_ko_s3_key: Mapped[str | None] = mapped_column(String(500))
    pdf_native_s3_key: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    description_translated: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[date | None] = mapped_column(Date, index=True)
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_precision: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    source: Mapped[str] = mapped_column(String(30), default="ai", nullable=False)
    source_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidences.id", ondelete="SET NULL"))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", _json_type())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TimelineEventEvidence(Base):
    __tablename__ = "timeline_event_evidences"
    __table_args__ = (UniqueConstraint("timeline_event_id", "evidence_id", "relation_type", name="uq_timeline_event_evidences_relation"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    timeline_event_id: Mapped[str] = mapped_column(ForeignKey("timeline_events.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_text_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_texts.id", ondelete="SET NULL"))
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidences.id", ondelete="SET NULL"))
    evidence_text_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_texts.id", ondelete="SET NULL"))
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    translation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    related_issue_type: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TranslationPair(Base):
    __tablename__ = "translation_pairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str | None] = mapped_column(String(50))
    related_issue: Mapped[str | None] = mapped_column(String(100))
    source_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidences.id", ondelete="SET NULL"))


class EvidencePack(Base):
    __tablename__ = "evidence_packs"
    __table_args__ = (UniqueConstraint("case_id", "pack_version", "language_code", name="uq_evidence_packs_case_version_language"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("case_analyses.id", ondelete="SET NULL"))
    pack_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), default="ko", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    pack_data: Mapped[dict] = mapped_column(_json_type(), nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EvidencePackFile(Base):
    __tablename__ = "evidence_pack_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evidence_pack_id: Mapped[str] = mapped_column(ForeignKey("evidence_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    file_hash_sha256: Mapped[str | None] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ko", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50))
    risk_level: Mapped[str | None] = mapped_column(String(30))
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_rag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_case_context: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    next_actions: Mapped[list | None] = mapped_column(_json_type())
    disclaimer: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_org: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column("language_code", String(10), default="ko", nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), default="guide", nullable=False, index=True)
    version: Mapped[str | None] = mapped_column(String(50))
    published_at: Mapped[date | None] = mapped_column(Date)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", _json_type())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks: Mapped[list[RagChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_rag_chunks_document_index"),)

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    keywords: Mapped[list | None] = mapped_column(_json_type())
    embedding: Mapped[list | None] = mapped_column(Vector(1024) if Vector else _json_type())
    metadata_json: Mapped[dict | None] = mapped_column("metadata", _json_type())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped[RagDocument] = relationship(back_populates="chunks")


class ChatMessageSource(Base):
    __tablename__ = "chat_message_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    chat_message_id: Mapped[str] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    rag_document_id: Mapped[str | None] = mapped_column(ForeignKey("rag_documents.id", ondelete="SET NULL"))
    rag_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("rag_chunks.id", ondelete="SET NULL"))
    source_title: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[float | None] = mapped_column(Numeric(8, 6))
    used_in_answer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", _json_type())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)
    related_case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"))
    related_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidences.id", ondelete="SET NULL"))
    related_pack_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_packs.id", ondelete="SET NULL"))
    payload: Mapped[dict | None] = mapped_column(_json_type())
    result: Mapped[dict | None] = mapped_column(_json_type())
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    ip_address: Mapped[str | None] = mapped_column(INET().with_variant(String(45), "sqlite"))
    user_agent: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", _json_type())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class Workplace(Base):
    __tablename__ = "workplaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    center_lat: Mapped[float] = mapped_column(Numeric(10, 7))
    center_lng: Mapped[float] = mapped_column(Numeric(10, 7))
    radius_m: Mapped[int] = mapped_column(Integer, default=50)


class GpsLog(Base):
    __tablename__ = "gps_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_delayed_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    lng: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    altitude_m: Mapped[float | None] = mapped_column(Numeric(8, 2))
    speed_mps: Mapped[float | None] = mapped_column(Numeric(6, 3))
    accuracy_m: Mapped[float | None] = mapped_column(Numeric(7, 2))
    provider: Mapped[str | None] = mapped_column(String(20))
    is_mocked: Mapped[bool] = mapped_column(Boolean, default=False)
    mock_reason: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(20))
    prev_chain_hash: Mapped[str | None] = mapped_column(String(64))
    chain_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(100))
    device_os: Mapped[str | None] = mapped_column(String(30))
    app_version: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20), default="app")
