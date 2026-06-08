from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..models import RagChunk, RagDocument
from .embedding_service import embed_text


@dataclass
class RetrievedChunk:
    source_id: str
    title: str
    source_org: str
    section: str | None
    text: str
    score: float
    retrieval_method: str

    def to_source(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "source_org": self.source_org,
            "section": self.section,
        }


def retrieve_rag_context(
    *,
    db: Session | None,
    question: str,
    intent: str,
    language: str,
) -> list[RetrievedChunk]:
    if not settings.rag_enabled or db is None:
        return []

    if settings.rag_use_vector and db.bind and db.bind.dialect.name == "postgresql":
        try:
            chunks = _retrieve_vector(db, question, language)
            if chunks:
                return chunks
        except Exception:
            pass

    return _retrieve_keyword(db, question, intent, language)


def format_rag_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "[]"
    items: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks, start=1):
        items.append(
            {
                "source_number": idx,
                "source_id": chunk.source_id,
                "title": chunk.title,
                "source_org": chunk.source_org,
                "section": chunk.section,
                "text": chunk.text,
            }
        )
    return str(items)


def _retrieve_vector(db: Session, question: str, language: str) -> list[RetrievedChunk]:
    query_embedding = embed_text(question)
    vector_literal = "[" + ",".join(str(float(v)) for v in query_embedding) + "]"
    rows = db.execute(
        text(
            """
            SELECT
                c.id AS chunk_id,
                c.section AS section,
                c.text AS chunk_text,
                d.id AS document_id,
                d.title AS title,
                d.source_org AS source_org,
                (c.embedding <=> CAST(:embedding AS vector)) AS distance
            FROM rag_chunks c
            JOIN rag_documents d ON d.id = c.document_id
            WHERE d.language IN (:language, 'ko', 'multi')
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        ),
        {
            "embedding": vector_literal,
            "language": language,
            "limit": settings.rag_top_k,
        },
    ).mappings()

    return [
        RetrievedChunk(
            source_id=row["document_id"],
            title=row["title"],
            source_org=row["source_org"],
            section=row["section"],
            text=row["chunk_text"],
            score=float(row["distance"]),
            retrieval_method="vector",
        )
        for row in rows
    ]


def _retrieve_keyword(db: Session, question: str, intent: str, language: str) -> list[RetrievedChunk]:
    query_terms = set(_keywords(question)) | set(_intent_terms(intent))
    if not query_terms:
        return []

    rows = (
        db.query(RagChunk, RagDocument)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .filter(RagDocument.language.in_([language, "ko", "multi"]))
        .all()
    )

    scored: list[RetrievedChunk] = []
    for chunk, doc in rows:
        chunk_terms = set(chunk.keywords or []) | set(_keywords(chunk.text))
        score = len(query_terms & chunk_terms)
        if score < settings.rag_min_keyword_score:
            continue
        scored.append(
            RetrievedChunk(
                source_id=doc.id,
                title=doc.title,
                source_org=doc.source_org,
                section=chunk.section,
                text=chunk.text,
                score=float(score),
                retrieval_method="keyword",
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[: settings.rag_top_k]


def _keywords(text_value: str) -> list[str]:
    return [
        token
        for token in re.split(r"[^0-9A-Za-z가-힣]+", text_value.lower())
        if len(token) >= 2
    ]


def _intent_terms(intent: str) -> list[str]:
    mapping = {
        "pack_summary": ["요약", "핵심", "자료", "패키지"],
        "consultation_script": ["상담", "순서", "질문", "설명"],
        "missing_document_explanation": ["누락", "자료", "준비", "추가"],
        "amount_difference_explanation": ["임금", "급여", "입금", "금액", "공제"],
        "preparation_guidance": ["준비", "상담", "자료"],
    }
    return mapping.get(intent, [])
