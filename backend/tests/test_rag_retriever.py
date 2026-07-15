from app.models import RagChunk, RagDocument
from app.services.rag_retriever import RetrievedChunk, retrieve_rag_context
from app.services.embedding_service import embed_text


def test_keyword_rag_retrieval(client, monkeypatch):
    monkeypatch.setattr("app.services.rag_retriever.settings.rag_use_vector", False)

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        doc = RagDocument(
            id="test-consult-prep",
            title="상담 준비 안내",
            source_org="고용노동부",
            source_url="https://www.moel.go.kr",
            language="ko",
            document_type="official_guide_summary",
            version="test",
            metadata_json={},
        )
        db.add(doc)
        db.add(
            RagChunk(
                id="test-consult-prep:0",
                document_id=doc.id,
                chunk_index=0,
                section="상담 순서",
                text="상담 전에는 근무기간, 약속한 임금, 실제 입금액, 증거 자료 순서로 설명을 준비한다.",
                token_count=10,
                keywords=["상담", "순서", "근무기간", "임금", "입금액", "증거"],
                embedding=embed_text("상담 전에는 근무기간, 약속한 임금, 실제 입금액, 증거 자료 순서로 설명을 준비한다."),
                metadata_json={},
            )
        )
        db.commit()

        chunks = retrieve_rag_context(
            db=db,
            question="상담하러 가면 뭐부터 말해야 해요?",
            intent="consultation_script",
            language="ko",
        )
    finally:
        db.close()

    assert chunks
    assert chunks[0].source_id == "test-consult-prep"
    assert chunks[0].section == "상담 순서"

def test_rag_source_includes_bounded_excerpt_and_retrieval_method():
    chunk = RetrievedChunk(
        source_id="official-guide",
        title="상담 준비 안내",
        source_org="고용노동부",
        section="준비 자료",
        text="  급여명세서와\n입금내역을 같은 기간으로 정리하세요.  " + ("추가 자료 " * 80),
        score=10.0,
        retrieval_method="hybrid",
    )

    source = chunk.to_source()

    assert source["excerpt"].startswith("급여명세서와 입금내역")
    assert "\n" not in source["excerpt"]
    assert len(source["excerpt"]) <= 323
    assert source["excerpt"].endswith("...")
    assert source["retrieval_method"] == "hybrid"
