from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import User
from app.schemas_community import CommunityCommentCreate, CommunityCommentUpdate, CommunityPostCreate, CommunityPostUpdate
from app.services.community_service import (
    create_comment,
    create_post,
    create_report,
    delete_comment,
    delete_post,
    list_posts,
    list_reports,
    safety_check,
    translate_text,
    update_comment,
    update_post,
    update_report_status,
)


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    user = User(email="community-test@bada.local", name="테스터", preferred_lang="ko")
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def test_community_safety_blocks_legal_judgment_questions():
    result = safety_check("이거 불법인가요? 바로 신고해야 하나요?", "ko")

    assert result.allowed is False
    assert result.risk_level == "blocked"
    assert result.moderation_status == "blocked"
    assert result.suggested_text


def test_community_safety_blocks_personal_information():
    examples = [
        "제 전화번호는 010-1234-5678이고 상담 가능한가요?",
        "외국인등록번호 900101-5123456도 같이 올립니다.",
        "답장은 worker@example.com 으로 주세요.",
        "계좌번호 123-456789-01-234 입니다.",
    ]

    for content in examples:
        result = safety_check(content, "ko")
        assert result.allowed is False
        assert result.risk_level == "privacy"
        assert result.moderation_status == "blocked"
        assert result.suggested_text


def test_community_safety_allows_profanity_without_privacy_or_legal_judgment():
    result = safety_check("사장이 진짜 짜증나고 욕 나오는데 입금내역은 어떻게 정리하면 좋을까요?", "ko")

    assert result.allowed is True
    assert result.risk_level in {"safe", "review"}


def test_community_safety_blocks_direct_legal_advice_requests():
    result = safety_check("이 상황에 대해 법률 조언 해주세요. 변호사처럼 판단해 주세요.", "ko")

    assert result.allowed is False
    assert result.risk_level == "blocked"


def test_community_safety_allows_consultation_preparation_questions():
    result = safety_check("진정서에 어떤 내용을 적으면 상담 준비에 도움이 되나요?", "ko")

    assert result.allowed is True
    assert result.risk_level in {"safe", "review"}


def test_community_translation_fallback_keeps_official_terms_annotated(monkeypatch):
    from app.services import community_service

    monkeypatch.setattr(community_service.settings, "ai_chat_mode", "mock")

    translated, provider = translate_text(
        "Tôi nhận được bảng lương ghi 2.300.000 KRW nhưng tài khoản chỉ vào 1.900.000 KRW. Tôi nên chuẩn bị những giấy tờ gì trước khi đi tư vấn?",
        "vi",
        "ko",
    )

    assert provider == "fallback"
    assert "급여명세서" in translated
    assert "입금내역" in translated


def test_community_post_update_and_delete():
    db, user = make_db()
    post = create_post(
        db,
        user,
        CommunityPostCreate(category="free", title="처음 제목", content="상담 준비 자료를 정리하고 싶어요.", language="ko"),
    )

    updated = update_post(
        db,
        user,
        post.id,
        CommunityPostUpdate(category="petition", title="수정 제목", content="진정서에 적을 내용을 정리하고 싶어요.", language="ko"),
    )
    assert updated.title == "수정 제목"
    assert updated.category == "petition"

    deleted = delete_post(db, user, post.id)
    assert deleted.status == "deleted"
    assert deleted.deleted_at is not None


def test_community_list_posts_searches_title_and_content():
    db, user = make_db()
    create_post(
        db,
        user,
        CommunityPostCreate(category="wage", title="입금내역 정리 질문", content="급여명세서와 통장 입금액을 비교하고 싶어요.", language="ko"),
    )
    create_post(
        db,
        user,
        CommunityPostCreate(category="petition", title="진정서 준비", content="상담 전에 가져갈 자료를 정리합니다.", language="ko"),
    )

    by_title = list_posts(db, user, search_query="입금내역")
    by_content = list_posts(db, user, search_query="통장")

    assert [post.title for post in by_title] == ["입금내역 정리 질문"]
    assert [post.title for post in by_content] == ["입금내역 정리 질문"]


def test_community_comment_update_and_delete_decrements_count():
    db, user = make_db()
    post = create_post(
        db,
        user,
        CommunityPostCreate(category="free", title="댓글 테스트", content="상담 전 자료를 준비하려고 합니다.", language="ko"),
    )
    comment = create_comment(
        db,
        user,
        post.id,
        CommunityCommentCreate(content="입금내역을 월별로 정리해 보세요.", language="ko"),
    )
    db.refresh(post)
    assert post.comment_count == 1

    updated = update_comment(
        db,
        user,
        comment.id,
        CommunityCommentUpdate(content="급여명세서와 입금내역을 월별로 정리해 보세요.", language="ko"),
    )
    assert "급여명세서" in updated.content

    deleted = delete_comment(db, user, comment.id)
    db.refresh(post)
    assert deleted.status == "deleted"
    assert post.comment_count == 0


def test_community_report_create_list_and_status_update():
    db, user = make_db()
    post = create_post(
        db,
        user,
        CommunityPostCreate(category="free", title="신고 테스트", content="상담 준비 질문입니다.", language="ko"),
    )

    report = create_report(
        db,
        user,
        target_type="post",
        target_id=post.id,
        reason="개인정보 포함 의심",
        description=None,
    )

    reports = list_reports(db, status="open")
    assert report.id in {row.id for row in reports}

    updated = update_report_status(db, report.id, "resolved")
    assert updated.status == "resolved"
