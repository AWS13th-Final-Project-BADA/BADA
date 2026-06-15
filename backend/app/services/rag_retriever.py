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

    keyword_chunks = _retrieve_keyword(
        db,
        question,
        intent,
        language,
        limit=max(settings.rag_top_k * 2, 8),
    )

    if settings.rag_use_vector and db.bind and db.bind.dialect.name == "postgresql":
        try:
            vector_chunks = _retrieve_vector(
                db,
                question,
                language,
                limit=max(settings.rag_top_k * 3, 12),
            )
            return _merge_ranked_chunks(
                question=question,
                intent=intent,
                vector_chunks=vector_chunks,
                keyword_chunks=keyword_chunks,
            )
        except Exception:
            pass

    return keyword_chunks[: settings.rag_top_k]


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


def _retrieve_vector(db: Session, question: str, language: str, limit: int) -> list[RetrievedChunk]:
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
            WHERE d.language_code IN (:language, 'ko', 'multi')
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        ),
        {
            "embedding": vector_literal,
            "language": language,
            "limit": limit,
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


def _retrieve_keyword(
    db: Session,
    question: str,
    intent: str,
    language: str,
    *,
    limit: int | None = None,
) -> list[RetrievedChunk]:
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
        title_terms = set(_keywords(doc.title)) | set(_keywords(chunk.section or ""))
        overlap = len(query_terms & chunk_terms)
        title_overlap = len(query_terms & title_terms)
        exact_bonus = _exact_match_bonus(question, doc.title, chunk.section, chunk.text)
        score = overlap + (title_overlap * 3) + exact_bonus
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
    return scored[: (limit or settings.rag_top_k)]


def _merge_ranked_chunks(
    *,
    question: str,
    intent: str,
    vector_chunks: list[RetrievedChunk],
    keyword_chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    query_terms = set(_keywords(question)) | set(_intent_terms(intent))
    merged: dict[tuple[str, str | None], RetrievedChunk] = {}

    for rank, chunk in enumerate(vector_chunks):
        key = (chunk.source_id, chunk.section)
        lexical = _lexical_score(query_terms, question, chunk)
        score = max(0.0, 15.0 - float(rank)) + lexical
        merged[key] = RetrievedChunk(
            source_id=chunk.source_id,
            title=chunk.title,
            source_org=chunk.source_org,
            section=chunk.section,
            text=chunk.text,
            score=score,
            retrieval_method="hybrid",
        )

    for chunk in keyword_chunks:
        key = (chunk.source_id, chunk.section)
        score = 35.0 + chunk.score
        if key in merged:
            merged[key].score += score
            merged[key].retrieval_method = "hybrid"
        else:
            merged[key] = RetrievedChunk(
                source_id=chunk.source_id,
                title=chunk.title,
                source_org=chunk.source_org,
                section=chunk.section,
                text=chunk.text,
                score=score,
                retrieval_method="hybrid",
            )

    ranked = sorted(merged.values(), key=lambda item: item.score, reverse=True)
    return ranked[: settings.rag_top_k]


def _lexical_score(query_terms: set[str], question: str, chunk: RetrievedChunk) -> float:
    text_terms = set(_keywords(chunk.text))
    title_terms = set(_keywords(chunk.title)) | set(_keywords(chunk.section or ""))
    return (
        len(query_terms & text_terms)
        + (len(query_terms & title_terms) * 3)
        + _exact_match_bonus(question, chunk.title, chunk.section, chunk.text)
    )


def _exact_match_bonus(question: str, title: str, section: str | None, text_value: str) -> int:
    bonus = 0
    terms = _keywords(question)
    haystacks = [title, section or "", text_value[:500]]
    for term in terms:
        for idx, value in enumerate(haystacks):
            if term in value.lower():
                bonus += 10 if idx < 2 else 2
    return bonus


def _keywords(text_value: str) -> list[str]:
    keywords: list[str] = []
    for token in re.split(r"[^0-9A-Za-z가-힣]+", text_value.lower()):
        if len(token) < 2:
            continue
        keywords.append(token)
        normalized = _strip_korean_particle(token)
        if normalized != token and len(normalized) >= 2:
            keywords.append(normalized)
    return keywords


def _strip_korean_particle(token: str) -> str:
    particles = (
        "에서는",
        "에게는",
        "으로는",
        "에는",
        "에서",
        "에게",
        "으로",
        "로는",
        "보다",
        "처럼",
        "까지",
        "부터",
        "하고",
        "이며",
        "이나",
        "거나",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "로",
        "과",
        "와",
        "도",
    )
    for particle in particles:
        if token.endswith(particle) and len(token) > len(particle) + 1:
            return token[: -len(particle)]
    return token


def _intent_terms(intent: str) -> list[str]:
    mapping = {
        "pack_summary": ["요약", "핵심", "자료", "패키지"],
        "consultation_script": ["상담", "순서", "질문", "설명"],
        "missing_document_explanation": ["누락", "자료", "준비", "추가"],
        "amount_difference_explanation": ["임금", "급여", "입금", "금액", "공제"],
        "preparation_guidance": ["준비", "상담", "자료"],
        "general_guidance": ["상담", "자료", "안내", "준비"],
    }
    return mapping.get(intent, [])
