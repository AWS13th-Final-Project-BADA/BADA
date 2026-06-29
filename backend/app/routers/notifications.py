"""알림 API — 조회, 읽음 처리, 생성(내부용)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user_id
from ..models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """내 알림 목록 (최신순, 최대 50개)."""
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "case_id": n.case_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """읽지 않은 알림 수."""
    count = db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).count()
    return {"count": count}


@router.patch("/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """알림 읽음 처리."""
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"ok": True}


@router.patch("/read-all")
def mark_all_read(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """모든 알림 읽음 처리."""
    db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"ok": True}


def create_notification(db: Session, user_id: str, type: str, title: str, body: str | None = None, case_id: str | None = None):
    """알림 생성 헬퍼 (내부에서 호출)."""
    n = Notification(user_id=user_id, type=type, title=title, body=body, case_id=case_id)
    db.add(n)
    db.commit()
    return n
