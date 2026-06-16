from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, check_db_connection, engine  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    CaseAnalysis,
    ChatMessage,
    ChatMessageSource,
    ChatSession,
    Evidence,
    EvidenceExtraction,
    EvidencePack,
    EvidencePackFile,
    EvidenceText,
    RagChunk,
    RagDocument,
    TimelineEvent,
    TimelineEventEvidence,
    Translation,
    User,
    UserLanguagePreference,
)


REQUIRED_TABLES = {
    "users",
    "user_language_preferences",
    "cases",
    "evidences",
    "evidence_texts",
    "evidence_extractions",
    "case_analyses",
    "timeline_events",
    "timeline_event_evidences",
    "translations",
    "evidence_packs",
    "evidence_pack_files",
    "chat_sessions",
    "chat_messages",
    "chat_message_sources",
    "rag_documents",
    "rag_chunks",
    "jobs",
    "audit_logs",
}


def main() -> None:
    result = check_db_connection()
    print(f"connection=ok dialect={result['dialect']}")

    tables = set(inspect(engine).get_table_names())
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        raise SystemExit(
            "missing_tables="
            + ", ".join(missing)
            + "\nRun: alembic upgrade head"
        )

    db = SessionLocal()
    try:
        user = User(email="smoke-test@bada.local", name="Smoke Test", preferred_lang="ko")
        db.add(user)
        db.flush()

        db.add(UserLanguagePreference(user_id=user.id, language_code="ko", priority=1))
        case = Case(user_id=user.id, title="Smoke test case", issue_type="wage_difference", workplace_name="Test workplace")
        db.add(case)
        db.flush()

        evidence = Evidence(
            case_id=case.id,
            user_id=user.id,
            category="payslip",
            file_type="text",
            file_name="smoke.txt",
            file_key="smoke/smoke.txt",
            mime_type="text/plain",
            file_size_bytes=12,
        )
        db.add(evidence)
        db.flush()

        text = EvidenceText(evidence_id=evidence.id, text_type="manual", language_code="ko", raw_text="급여명세서 테스트")
        db.add(text)
        db.flush()
        db.add(EvidenceExtraction(evidence_id=evidence.id, extraction_type="amounts", extracted_json={"amount": 1000}))

        analysis = CaseAnalysis(
            case_id=case.id,
            analysis_version=1,
            status="succeeded",
            difference_amount=400000,
            missing_documents=["근무시간 기록"],
            analysis_disclaimer="상담 전 정리 결과이며 법률 판단이 아닙니다.",
        )
        db.add(analysis)
        db.flush()

        event = TimelineEvent(case_id=case.id, event_type="deposit", title="입금내역 확인", source="user")
        db.add(event)
        db.flush()
        db.add(TimelineEventEvidence(timeline_event_id=event.id, evidence_id=evidence.id, evidence_text_id=text.id, relation_type="supports"))

        db.add(
            Translation(
                case_id=case.id,
                evidence_id=evidence.id,
                evidence_text_id=text.id,
                source_language="vi",
                target_language="ko",
                source_text="test",
                translated_text="테스트",
                translation_type="memo",
            )
        )

        pack = EvidencePack(
            case_id=case.id,
            analysis_id=analysis.id,
            pack_version=1,
            language_code="ko",
            pack_data={"summary": "smoke"},
            disclaimer="PDF는 결과물이며 pack_data가 원본 스냅샷입니다.",
        )
        db.add(pack)
        db.flush()
        db.add(
            EvidencePackFile(
                evidence_pack_id=pack.id,
                case_id=case.id,
                language_code="ko",
                file_format="pdf",
                s3_bucket="smoke",
                s3_key="packs/smoke.pdf",
            )
        )

        rag_doc = RagDocument(id="smoke-rag-doc", title="Smoke RAG", source_org="BADA", language="ko", document_type="guide")
        db.add(rag_doc)
        db.flush()
        rag_chunk = RagChunk(
            id="smoke-rag-doc:0",
            document_id=rag_doc.id,
            chunk_index=0,
            section="테스트",
            text="상담 전 자료를 정리합니다.",
            token_count=4,
            keywords=["상담", "자료"],
            embedding=[0.0] * 1024,
        )
        db.add(rag_chunk)
        db.flush()

        session = ChatSession(user_id=user.id, case_id=case.id, language_code="ko")
        db.add(session)
        db.flush()
        message = ChatMessage(
            session_id=session.id,
            case_id=case.id,
            role="assistant",
            message="상담 전 자료를 정리해보겠습니다.",
            language_code="ko",
            intent="preparation_guidance",
            risk_level="safe",
            used_rag=True,
            used_case_context=True,
        )
        db.add(message)
        db.flush()
        db.add(
            ChatMessageSource(
                chat_message_id=message.id,
                rag_document_id=rag_doc.id,
                rag_chunk_id=rag_chunk.id,
                source_title=rag_doc.title,
                relevance_score=0.9,
            )
        )

        db.flush()
        print("smoke_insert=ok rollback=true")
    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    main()
