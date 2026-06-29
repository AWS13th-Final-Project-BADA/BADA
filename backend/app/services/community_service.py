from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    CommunityComment,
    CommunityPost,
    CommunityReaction,
    CommunityReport,
    CommunityTranslation,
    User,
)
from ..schemas_community import (
    CommunityCommentCreate,
    CommunityCommentResponse,
    CommunityCommentUpdate,
    CommunityPostCreate,
    CommunityPostResponse,
    CommunityPostUpdate,
    CommunitySafetyResponse,
)
from .language_service import detect_message_language, language_name, normalize_language_code, resolve_chat_language
from .legal_risk_classifier import classify_legal_risk
from .terminology_service import annotate_terms_for_language

logger = logging.getLogger(__name__)


CATEGORY_LABELS = {
    "free": "자유게시판",
    "wage": "임금/공제",
    "petition": "진정서",
    "review": "상담 후기",
    "translation": "번역 피드",
    "notice": "공지",
}

PERSONAL_INFO_PATTERNS = [
    # Email.
    r"\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b",
    # Korean mobile/phone numbers.
    r"(?<!\d)(?:01[016789]|02|0[3-6][1-5])[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)",
    # Korean resident registration / alien registration number shape.
    r"(?<!\d)\d{6}[-\s]?[1-8]\d{6}(?!\d)",
    # Explicit ID/passport/account-number contexts. Avoid blocking ordinary wage amounts.
    r"(주민등록번호|외국인등록번호|등록번호|여권번호|신분증번호|passport\s*number|alien\s*registration|arc\s*number|id\s*number|số\s*(hộ\s*chiếu|đăng\s*ký|cmnd|cccd))[^0-9]{0,24}[a-z0-9\-]{5,}",
    r"(계좌번호|은행\s*계좌|bank\s*account|account\s*number|số\s*tài\s*khoản)[^0-9]{0,24}[0-9\-\s]{8,}",
]


def safety_check(content: str, language: str = "auto") -> CommunitySafetyResponse:
    resolved_language = resolve_chat_language(language, content)
    if _contains_personal_info(content):
        return CommunitySafetyResponse(
            allowed=False,
            risk_level="privacy",
            moderation_status="blocked",
            language=resolved_language,
            message=_privacy_message(resolved_language),
            suggested_text=_privacy_rewrite_hint(resolved_language),
        )

    risk_level, blocked = classify_legal_risk(content)
    moderation_status = "blocked" if blocked else ("review" if risk_level == "review" else "passed")

    if blocked:
        return CommunitySafetyResponse(
            allowed=False,
            risk_level=risk_level,
            moderation_status=moderation_status,
            language=resolved_language,
            message=_blocked_message(resolved_language),
            suggested_text=_safe_rewrite_hint(resolved_language),
        )

    return CommunitySafetyResponse(
        allowed=True,
        risk_level=risk_level,
        moderation_status=moderation_status,
        language=resolved_language,
        message=_passed_message(resolved_language, risk_level),
        suggested_text=None,
    )


def create_post(db: Session, user: User, payload: CommunityPostCreate) -> CommunityPost:
    safety = safety_check(f"{payload.title}\n{payload.content}", payload.language)
    if not safety.allowed:
        raise HTTPException(status_code=422, detail=safety.model_dump())

    post = CommunityPost(
        user_id=user.id,
        anonymous_name=payload.anonymous_name or _anonymous_name(user.id),
        category=payload.category,
        title=payload.title.strip(),
        content=payload.content.strip(),
        language_code=safety.language,
        moderation_status=safety.moderation_status,
        risk_level=safety.risk_level,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, user: User, post_id: str, payload: CommunityPostUpdate) -> CommunityPost:
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "published" or post.deleted_at is not None:
        raise HTTPException(status_code=404, detail="post not found")
    _assert_owner(user, post.user_id)

    new_title = payload.title.strip() if payload.title is not None else post.title
    new_content = payload.content.strip() if payload.content is not None else post.content
    new_category = payload.category or post.category

    safety = safety_check(f"{new_title}\n{new_content}", payload.language)
    if not safety.allowed:
        raise HTTPException(status_code=422, detail=safety.model_dump())

    post.title = new_title
    post.content = new_content
    post.category = new_category
    post.language_code = safety.language
    post.moderation_status = safety.moderation_status
    post.risk_level = safety.risk_level
    post.updated_at = _now()
    _delete_translations(db, "post", post.id)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, user: User, post_id: str) -> CommunityPost:
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "published" or post.deleted_at is not None:
        raise HTTPException(status_code=404, detail="post not found")
    _assert_owner(user, post.user_id)

    post.status = "deleted"
    post.deleted_at = _now()
    post.updated_at = _now()
    _delete_translations(db, "post", post.id)
    db.commit()
    db.refresh(post)
    return post


def create_comment(db: Session, user: User, post_id: str, payload: CommunityCommentCreate) -> CommunityComment:
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "published":
        raise HTTPException(status_code=404, detail="post not found")

    safety = safety_check(payload.content, payload.language)
    if not safety.allowed:
        raise HTTPException(status_code=422, detail=safety.model_dump())

    parent = None
    if payload.parent_comment_id:
        parent = db.get(CommunityComment, payload.parent_comment_id)
        if not parent or parent.post_id != post_id:
            raise HTTPException(status_code=404, detail="parent comment not found")

    comment = CommunityComment(
        post_id=post_id,
        user_id=user.id,
        parent_comment_id=payload.parent_comment_id,
        anonymous_name=payload.anonymous_name or _comment_name(user.id),
        content=payload.content.strip(),
        language_code=safety.language,
        moderation_status=safety.moderation_status,
        risk_level=safety.risk_level,
    )
    db.add(comment)
    post.comment_count += 1
    if parent:
        parent.reply_count += 1
    db.commit()
    db.refresh(comment)
    return comment


def list_comments(db: Session, user: User, post_id: str, limit: int = 50) -> list[CommunityCommentResponse]:
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "published" or post.deleted_at is not None:
        raise HTTPException(status_code=404, detail="post not found")

    comments = (
        db.query(CommunityComment)
        .filter(
            CommunityComment.post_id == post_id,
            CommunityComment.status == "published",
            CommunityComment.deleted_at.is_(None),
        )
        .order_by(CommunityComment.created_at.asc())
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return [serialize_comment(db, comment, user) for comment in comments]


def get_comment(db: Session, user: User, comment_id: str) -> CommunityCommentResponse:
    comment = db.get(CommunityComment, comment_id)
    if not comment or comment.status != "published" or comment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="comment not found")
    return serialize_comment(db, comment, user)


def update_comment(db: Session, user: User, comment_id: str, payload: CommunityCommentUpdate) -> CommunityComment:
    comment = db.get(CommunityComment, comment_id)
    if not comment or comment.status != "published" or comment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="comment not found")
    _assert_owner(user, comment.user_id)

    safety = safety_check(payload.content, payload.language)
    if not safety.allowed:
        raise HTTPException(status_code=422, detail=safety.model_dump())

    comment.content = payload.content.strip()
    comment.language_code = safety.language
    comment.moderation_status = safety.moderation_status
    comment.risk_level = safety.risk_level
    comment.updated_at = _now()
    _delete_translations(db, "comment", comment.id)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, user: User, comment_id: str) -> CommunityComment:
    comment = db.get(CommunityComment, comment_id)
    if not comment or comment.status != "published" or comment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="comment not found")
    _assert_owner(user, comment.user_id)

    post = db.get(CommunityPost, comment.post_id)
    if post:
        post.comment_count = max(0, post.comment_count - 1)
        post.updated_at = _now()
    if comment.parent_comment_id:
        parent = db.get(CommunityComment, comment.parent_comment_id)
        if parent:
            parent.reply_count = max(0, parent.reply_count - 1)

    comment.status = "deleted"
    comment.deleted_at = _now()
    comment.updated_at = _now()
    _delete_translations(db, "comment", comment.id)
    db.commit()
    db.refresh(comment)
    return comment


def list_posts(
    db: Session,
    user: User,
    *,
    category: str | None = None,
    sort: str = "hot",
    language: str | None = None,
    search_query: str | None = None,
    mine: bool = False,
    limit: int = 20,
) -> list[CommunityPostResponse]:
    db_query = db.query(CommunityPost).filter(CommunityPost.status == "published", CommunityPost.deleted_at.is_(None))
    if mine:
        db_query = db_query.filter(CommunityPost.user_id == user.id)
    if category and category != "all":
        db_query = db_query.filter(CommunityPost.category == category)
    if language and language != "all":
        db_query = db_query.filter(CommunityPost.language_code == normalize_language_code(language))
    if query_text := (search_query or "").strip():
        keyword = f"%{query_text}%"
        db_query = db_query.filter(or_(CommunityPost.title.ilike(keyword), CommunityPost.content.ilike(keyword)))

    if sort == "latest":
        db_query = db_query.order_by(CommunityPost.created_at.desc())
    else:
        db_query = db_query.order_by((CommunityPost.like_count + CommunityPost.comment_count + CommunityPost.saved_count).desc(), CommunityPost.created_at.desc())

    posts = db_query.limit(min(max(limit, 1), 50)).all()
    return [serialize_post(db, post, user) for post in posts]


def get_post(db: Session, user: User, post_id: str) -> CommunityPostResponse:
    post = db.get(CommunityPost, post_id)
    if not post or post.status != "published":
        raise HTTPException(status_code=404, detail="post not found")
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return serialize_post(db, post, user, comments_limit=30)


def toggle_reaction(db: Session, user: User, *, target_type: str, target_id: str, reaction_type: str) -> tuple[bool, int | None, int | None]:
    target = _get_target(db, target_type, target_id)
    if reaction_type == "save" and target_type != "post":
        raise HTTPException(status_code=400, detail="comments cannot be saved")

    existing = (
        db.query(CommunityReaction)
        .filter(
            CommunityReaction.user_id == user.id,
            CommunityReaction.target_type == target_type,
            CommunityReaction.target_id == target_id,
            CommunityReaction.reaction_type == reaction_type,
        )
        .first()
    )
    active = existing is None
    if existing:
        db.delete(existing)
        _apply_count(target, reaction_type, -1)
    else:
        db.add(CommunityReaction(user_id=user.id, target_type=target_type, target_id=target_id, reaction_type=reaction_type))
        _apply_count(target, reaction_type, 1)

    db.commit()
    db.refresh(target)
    return active, getattr(target, "like_count", None), getattr(target, "saved_count", None)


def _encode_post_translation(title: str, content: str) -> str:
    return json.dumps({"title": title, "content": content}, ensure_ascii=False)


def _decode_post_translation(value: str) -> tuple[str | None, str]:
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None, value
    if not isinstance(payload, dict):
        return None, value
    title = payload.get("title")
    content = payload.get("content")
    if isinstance(title, str) and isinstance(content, str):
        return title, content
    return None, value


def translate_target(
    db: Session,
    *,
    target_type: str,
    target_id: str,
    target_language: str,
) -> tuple[str, str, str, str, bool, str | None, str]:
    target = _get_target(db, target_type, target_id)
    target_language = normalize_language_code(target_language)
    source_language = getattr(target, "language_code", None) or detect_message_language(target.content)
    if source_language == target_language:
        title = target.title if target_type == "post" else None
        return source_language, target_language, target.content, "identity", True, title, target.content

    cached = (
        db.query(CommunityTranslation)
        .filter(
            CommunityTranslation.target_type == target_type,
            CommunityTranslation.target_id == target_id,
            CommunityTranslation.target_language == target_language,
        )
        .first()
    )
    if cached:
        if target_type == "post":
            translated_title, translated_content = _decode_post_translation(cached.translated_text)
            if translated_title is None:
                translated_title, _ = translate_text(target.title, source_language, target_language)
                cached.translated_text = _encode_post_translation(translated_title, translated_content)
                db.commit()
            return (
                cached.source_language,
                cached.target_language,
                translated_content,
                cached.provider,
                True,
                translated_title,
                translated_content,
            )
        return (
            cached.source_language,
            cached.target_language,
            cached.translated_text,
            cached.provider,
            True,
            None,
            cached.translated_text,
        )

    translated_content, provider = translate_text(target.content, source_language, target_language)
    translated_title = None
    cached_text = translated_content
    if target_type == "post":
        translated_title, _ = translate_text(target.title, source_language, target_language)
        cached_text = _encode_post_translation(translated_title, translated_content)
    row = CommunityTranslation(
        target_type=target_type,
        target_id=target_id,
        source_language=source_language,
        target_language=target_language,
        translated_text=cached_text,
        provider=provider,
        cached=True,
    )
    db.add(row)
    db.commit()
    return (
        source_language,
        target_language,
        translated_content,
        provider,
        False,
        translated_title,
        translated_content,
    )


def translate_text(text: str, source_language: str, target_language: str) -> tuple[str, str]:
    source_language = normalize_language_code(source_language)
    target_language = normalize_language_code(target_language)
    if source_language == target_language:
        return text, "identity"

    if settings.ai_chat_mode.lower() == "bedrock":
        try:
            return _translate_with_bedrock(text, source_language, target_language), "bedrock"
        except Exception as exc:
            logger.warning("Community translation failed; using fallback: %s", exc)

    return _fallback_translate(text, source_language, target_language), "fallback"


def create_report(db: Session, user: User, *, target_type: str, target_id: str, reason: str, description: str | None) -> CommunityReport:
    target = _get_target(db, target_type, target_id)
    report = CommunityReport(
        reporter_id=user.id,
        target_type=target_type,
        target_id=target_id,
        reason=reason.strip(),
        description=description.strip() if description else None,
    )
    db.add(report)
    target.report_count += 1
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, *, status: str | None = None, limit: int = 100) -> list[CommunityReport]:
    query = db.query(CommunityReport)
    if status and status != "all":
        query = query.filter(CommunityReport.status == status)
    return query.order_by(CommunityReport.created_at.desc()).limit(min(max(limit, 1), 200)).all()


def update_report_status(db: Session, report_id: str, status: str) -> CommunityReport:
    report = db.get(CommunityReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    report.status = status
    db.commit()
    db.refresh(report)
    return report


def board_summaries(db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category, label in CATEGORY_LABELS.items():
        count = db.query(CommunityPost).filter(CommunityPost.category == category, CommunityPost.status == "published").count()
        rows.append({"category": category, "label": label, "post_count": count, "unread_count": min(count, 99)})
    return rows


def serialize_post(db: Session, post: CommunityPost, user: User, comments_limit: int = 2) -> CommunityPostResponse:
    comments = (
        db.query(CommunityComment)
        .filter(
            CommunityComment.post_id == post.id,
            CommunityComment.parent_comment_id.is_(None),
            CommunityComment.status == "published",
            CommunityComment.deleted_at.is_(None),
        )
        .order_by((CommunityComment.like_count + CommunityComment.reply_count).desc(), CommunityComment.created_at.asc())
        .limit(comments_limit)
        .all()
    )
    return CommunityPostResponse(
        id=post.id,
        category=post.category,
        title=post.title,
        content=annotate_terms_for_language(post.content, post.language_code),
        language_code=post.language_code,
        anonymous_name=post.anonymous_name,
        status=post.status,
        moderation_status=post.moderation_status,
        risk_level=post.risk_level,
        like_count=post.like_count,
        comment_count=post.comment_count,
        saved_count=post.saved_count,
        view_count=post.view_count,
        created_at=post.created_at,
        my_liked=_has_reaction(db, user.id, "post", post.id, "like"),
        my_saved=_has_reaction(db, user.id, "post", post.id, "save"),
        my_owned=post.user_id == user.id,
        comments_preview=[serialize_comment(db, comment, user) for comment in comments],
    )


def serialize_comment(db: Session, comment: CommunityComment, user: User) -> CommunityCommentResponse:
    return CommunityCommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        parent_comment_id=comment.parent_comment_id,
        anonymous_name=comment.anonymous_name,
        content=annotate_terms_for_language(comment.content, comment.language_code),
        language_code=comment.language_code,
        status=comment.status,
        moderation_status=comment.moderation_status,
        risk_level=comment.risk_level,
        like_count=comment.like_count,
        reply_count=comment.reply_count,
        created_at=comment.created_at,
        my_liked=_has_reaction(db, user.id, "comment", comment.id, "like"),
        my_owned=comment.user_id == user.id,
    )


def _translate_with_bedrock(text: str, source_language: str, target_language: str) -> str:
    import boto3

    session = (
        boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
        if settings.aws_profile
        else boto3.Session(region_name=settings.aws_region)
    )
    client = session.client("bedrock-runtime")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 700,
        "system": (
            "You translate short community posts and comments for migrant workers in Korea. "
            "Return only the translated text. Do not add legal judgment. Keep official Korean terms and add short parentheses when useful."
        ),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Translate from {language_name(source_language)} to {language_name(target_language)}.\n"
                            f"Text:\n{text[:3000]}"
                        ),
                    }
                ],
            }
        ],
    }
    response = client.invoke_model(
        modelId=settings.bedrock_model_id,
        body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    raw = json.loads(response["body"].read().decode("utf-8"))
    parts = [
        item.get("text", "")
        for item in raw.get("content", [])
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    translated = "\n".join(part for part in parts if part).strip()
    if not translated:
        raise RuntimeError("empty translation")
    return annotate_terms_for_language(translated, target_language)


def _fallback_translate(text: str, source_language: str, target_language: str) -> str:
    if target_language == "vi":
        return annotate_terms_for_language(text, "vi")
    if target_language == "ko":
        known = {
            "Tôi nhận được bảng lương ghi 2.300.000 KRW nhưng tài khoản chỉ vào 1.900.000 KRW. Tôi nên chuẩn bị những giấy tờ gì trước khi đi tư vấn?":
                "급여명세서(bảng lương)에는 2,300,000원이 적혀 있는데 입금내역(lịch sử chuyển khoản)은 1,900,000원입니다. 상담 전에 어떤 자료를 준비하면 좋을까요?",
            "Bạn nên ghi lại tiền ký túc xá và tiền ăn bị trừ mỗi tháng.":
                "매달 공제된 기숙사비(phí ký túc xá)와 식비(tiền ăn)를 메모해두면 좋아요.",
        }
        return known.get(text, text)
    return text


def _get_target(db: Session, target_type: str, target_id: str) -> CommunityPost | CommunityComment:
    if target_type == "post":
        target = db.get(CommunityPost, target_id)
    elif target_type == "comment":
        target = db.get(CommunityComment, target_id)
    else:
        raise HTTPException(status_code=400, detail="invalid target_type")
    if not target or target.status != "published":
        raise HTTPException(status_code=404, detail="target not found")
    return target


def _apply_count(target: CommunityPost | CommunityComment, reaction_type: str, delta: int) -> None:
    if reaction_type == "like":
        target.like_count = max(0, target.like_count + delta)
    elif reaction_type == "save" and isinstance(target, CommunityPost):
        target.saved_count = max(0, target.saved_count + delta)


def _has_reaction(db: Session, user_id: str, target_type: str, target_id: str, reaction_type: str) -> bool:
    return (
        db.query(CommunityReaction)
        .filter(
            CommunityReaction.user_id == user_id,
            CommunityReaction.target_type == target_type,
            CommunityReaction.target_id == target_id,
            CommunityReaction.reaction_type == reaction_type,
        )
        .first()
        is not None
    )


def _contains_personal_info(content: str) -> bool:
    text = re.sub(r"\s+", " ", content.lower().strip())
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in PERSONAL_INFO_PATTERNS)


def _assert_owner(user: User, owner_id: str) -> None:
    if user.id != owner_id:
        raise HTTPException(status_code=403, detail="not your community content")


def _delete_translations(db: Session, target_type: str, target_id: str) -> None:
    (
        db.query(CommunityTranslation)
        .filter(
            CommunityTranslation.target_type == target_type,
            CommunityTranslation.target_id == target_id,
        )
        .delete(synchronize_session=False)
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _anonymous_name(user_id: str) -> str:
    return f"익명 근로자 {abs(hash(user_id)) % 900 + 100}"


def _comment_name(user_id: str) -> str:
    return f"익명 {abs(hash(user_id)) % 90 + 10}"


def _blocked_message(language: str) -> str:
    if language == "vi":
        return "Câu này cần đánh giá pháp lý nên không thể đăng nguyên văn."
    if language == "en":
        return "This needs legal judgment, so it cannot be posted as written."
    return "법률 판단이 필요한 표현이라 그대로 게시할 수 없어요."


def _privacy_message(language: str) -> str:
    if language == "vi":
        return "Có vẻ có thông tin cá nhân. Hãy xóa hoặc che thông tin nhận dạng trước khi đăng."
    if language == "en":
        return "This appears to include personal information. Remove or mask identifying details before posting."
    return "개인정보가 포함된 것 같아요. 게시 전에 식별 가능한 정보를 지우거나 가려 주세요."


def _passed_message(language: str, risk_level: str) -> str:
    if language == "vi":
        return "Có thể đăng. Nếu nội dung quan trọng, hãy xác nhận lại khi tư vấn." if risk_level == "safe" else "Có thể đăng, nhưng nên giữ cách diễn đạt chuẩn bị tư vấn."
    if language == "en":
        return "Ready to post. Please confirm important details during consultation." if risk_level == "safe" else "Ready to post, but keep it framed as consultation preparation."
    return "게시할 수 있어요. 중요한 내용은 상담에서 다시 확인하세요." if risk_level == "safe" else "게시할 수 있지만 상담 준비형 표현을 유지하는 게 좋아요."


def _privacy_rewrite_hint(language: str) -> str:
    if language == "vi":
        return "Ví dụ: tên, số điện thoại, số đăng ký, số hộ chiếu và số tài khoản nên được che như ***."
    if language == "en":
        return "Example: mask names, phone numbers, registration numbers, passport numbers, and account numbers as ***."
    return "예: 이름, 전화번호, 등록번호, 여권번호, 계좌번호는 ***처럼 가리고 작성해 주세요."


def _safe_rewrite_hint(language: str) -> str:
    if language == "vi":
        return "Dựa trên tài liệu hiện có, tôi muốn chuẩn bị câu hỏi để trung tâm tư vấn xác nhận."
    if language == "en":
        return "Based on my current materials, I want to prepare questions for a counseling center to confirm."
    return "현재 자료 기준으로 상담기관에서 확인받을 질문을 준비하고 싶습니다."
