from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas_community import (
    CommunityBoardsResponse,
    CommunityCommentCreate,
    CommunityCommentResponse,
    CommunityCommentsResponse,
    CommunityCommentUpdate,
    CommunityDeleteResponse,
    CommunityFeedResponse,
    CommunityPostCreate,
    CommunityPostResponse,
    CommunityPostUpdate,
    CommunityReportDetailResponse,
    CommunityReactionRequest,
    CommunityReactionResponse,
    CommunityReportRequest,
    CommunityReportResponse,
    CommunityReportsResponse,
    CommunityReportStatusUpdate,
    CommunitySafetyRequest,
    CommunitySafetyResponse,
    CommunityTranslationRequest,
    CommunityTranslationResponse,
)
from ..services.community_service import (
    board_summaries,
    create_comment,
    create_post,
    create_report,
    delete_comment,
    delete_post,
    get_comment,
    get_post,
    list_comments,
    list_posts,
    list_reports,
    safety_check,
    serialize_comment,
    serialize_post,
    toggle_reaction,
    translate_target,
    update_comment,
    update_post,
    update_report_status,
)

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/posts", response_model=CommunityFeedResponse)
def community_feed(
    category: str | None = Query(default=None),
    sort: str = Query(default="hot"),
    language: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=80),
    mine: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return {"posts": list_posts(db, user, category=category, sort=sort, language=language, search_query=q, mine=mine, limit=limit)}


@router.post("/posts", response_model=CommunityPostResponse)
def community_create_post(
    payload: CommunityPostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = create_post(db, user, payload)
    return serialize_post(db, post, user)


@router.get("/posts/{post_id}", response_model=CommunityPostResponse)
def community_get_post(
    post_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_post(db, user, post_id)


@router.patch("/posts/{post_id}", response_model=CommunityPostResponse)
def community_update_post(
    post_id: str,
    payload: CommunityPostUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = update_post(db, user, post_id, payload)
    return serialize_post(db, post, user)


@router.delete("/posts/{post_id}", response_model=CommunityDeleteResponse)
def community_delete_post(
    post_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = delete_post(db, user, post_id)
    return {"id": post.id, "status": post.status, "deleted": True}


@router.get("/posts/{post_id}/comments", response_model=CommunityCommentsResponse)
def community_list_comments(
    post_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return {"comments": list_comments(db, user, post_id, limit=limit)}


@router.post("/posts/{post_id}/comments", response_model=CommunityCommentResponse)
def community_create_comment(
    post_id: str,
    payload: CommunityCommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = create_comment(db, user, post_id, payload)
    return serialize_comment(db, comment, user)


@router.get("/comments/{comment_id}", response_model=CommunityCommentResponse)
def community_get_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_comment(db, user, comment_id)


@router.patch("/comments/{comment_id}", response_model=CommunityCommentResponse)
def community_update_comment(
    comment_id: str,
    payload: CommunityCommentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = update_comment(db, user, comment_id, payload)
    return serialize_comment(db, comment, user)


@router.delete("/comments/{comment_id}", response_model=CommunityDeleteResponse)
def community_delete_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = delete_comment(db, user, comment_id)
    return {"id": comment.id, "status": comment.status, "deleted": True}


@router.post("/reactions", response_model=CommunityReactionResponse)
def community_toggle_reaction(
    payload: CommunityReactionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    active, like_count, saved_count = toggle_reaction(
        db,
        user,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reaction_type=payload.reaction_type,
    )
    return {"active": active, "like_count": like_count, "saved_count": saved_count}


@router.post("/translate", response_model=CommunityTranslationResponse)
def community_translate(
    payload: CommunityTranslationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    source_language, target_language, translated_text, provider, cached = translate_target(
        db,
        target_type=payload.target_type,
        target_id=payload.target_id,
        target_language=payload.target_language,
    )
    return {
        "target_type": payload.target_type,
        "target_id": payload.target_id,
        "source_language": source_language,
        "target_language": target_language,
        "translated_text": translated_text,
        "provider": provider,
        "cached": cached,
    }


@router.post("/reports", response_model=CommunityReportResponse)
def community_report(
    payload: CommunityReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = create_report(
        db,
        user,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        description=payload.description,
    )
    return {"id": report.id, "status": report.status}


@router.get("/reports", response_model=CommunityReportsResponse)
def community_reports(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ = user
    return {"reports": [serialize_report(report) for report in list_reports(db, status=status, limit=limit)]}


@router.patch("/reports/{report_id}", response_model=CommunityReportDetailResponse)
def community_update_report(
    report_id: str,
    payload: CommunityReportStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ = user
    return serialize_report(update_report_status(db, report_id, payload.status))


@router.post("/safety-check", response_model=CommunitySafetyResponse)
def community_safety_check(payload: CommunitySafetyRequest):
    return safety_check(payload.content, payload.language)


@router.get("/boards", response_model=CommunityBoardsResponse)
def community_boards(db: Session = Depends(get_db)):
    return {"boards": board_summaries(db)}


def serialize_report(report) -> dict:
    return {
        "id": report.id,
        "reporter_id": report.reporter_id,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "reason": report.reason,
        "description": report.description,
        "status": report.status,
        "created_at": report.created_at,
    }
