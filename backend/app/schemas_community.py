from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


CommunityCategory = Literal["free", "wage", "petition", "review", "translation", "notice"]
CommunityTargetType = Literal["post", "comment"]
CommunityReactionType = Literal["like", "save"]


class CommunitySafetyRequest(BaseModel):
    content: str
    language: str = "auto"


class CommunitySafetyResponse(BaseModel):
    allowed: bool
    risk_level: str
    moderation_status: str
    language: str
    message: str
    suggested_text: str | None = None


class CommunityPostCreate(BaseModel):
    category: CommunityCategory = "free"
    title: str = Field(min_length=2, max_length=160)
    content: str = Field(min_length=2, max_length=5000)
    language: str = "auto"
    anonymous_name: str | None = None


class CommunityPostUpdate(BaseModel):
    category: CommunityCategory | None = None
    title: str | None = Field(default=None, min_length=2, max_length=160)
    content: str | None = Field(default=None, min_length=2, max_length=5000)
    language: str = "auto"


class CommunityCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    language: str = "auto"
    parent_comment_id: str | None = None
    anonymous_name: str | None = None


class CommunityCommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    language: str = "auto"


class CommunityDeleteResponse(BaseModel):
    id: str
    status: str
    deleted: bool


class CommunityCommentResponse(BaseModel):
    id: str
    post_id: str
    parent_comment_id: str | None
    anonymous_name: str
    content: str
    language_code: str
    status: str
    moderation_status: str
    risk_level: str
    like_count: int
    reply_count: int
    created_at: datetime
    my_liked: bool = False
    my_owned: bool = False


class CommunityPostResponse(BaseModel):
    id: str
    category: str
    title: str
    content: str
    language_code: str
    anonymous_name: str
    status: str
    moderation_status: str
    risk_level: str
    like_count: int
    comment_count: int
    saved_count: int
    view_count: int
    created_at: datetime
    my_liked: bool = False
    my_saved: bool = False
    my_owned: bool = False
    comments_preview: list[CommunityCommentResponse] = Field(default_factory=list)


class CommunityFeedResponse(BaseModel):
    posts: list[CommunityPostResponse]


class CommunityCommentsResponse(BaseModel):
    comments: list[CommunityCommentResponse]


class CommunityReactionRequest(BaseModel):
    target_type: CommunityTargetType
    target_id: str
    reaction_type: CommunityReactionType


class CommunityReactionResponse(BaseModel):
    active: bool
    like_count: int | None = None
    saved_count: int | None = None


class CommunityTranslationRequest(BaseModel):
    target_type: CommunityTargetType
    target_id: str
    target_language: str


class CommunityTranslationResponse(BaseModel):
    target_type: str
    target_id: str
    source_language: str
    target_language: str
    translated_text: str
    provider: str
    cached: bool


class CommunityReportRequest(BaseModel):
    target_type: CommunityTargetType
    target_id: str
    reason: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)


class CommunityReportResponse(BaseModel):
    id: str
    status: str


class CommunityReportDetailResponse(BaseModel):
    id: str
    reporter_id: str
    target_type: str
    target_id: str
    reason: str
    description: str | None
    status: str
    created_at: datetime


class CommunityReportsResponse(BaseModel):
    reports: list[CommunityReportDetailResponse]


class CommunityReportStatusUpdate(BaseModel):
    status: Literal["open", "reviewing", "resolved", "dismissed"]


class CommunityBoardSummary(BaseModel):
    category: str
    label: str
    post_count: int
    unread_count: int = 0


class CommunityBoardsResponse(BaseModel):
    boards: list[CommunityBoardSummary]
