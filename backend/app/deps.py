"""공통 의존성 — 인증. 모든 라우터가 같은 seam을 쓴다.

로컬: 데모 유저 자동 생성. AWS: Cognito JWT 검증으로 교체(인증 담당).
교체 지점은 `get_current_user` 한 곳뿐 — 라우터는 건드리지 않는다.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

DEMO_EMAIL = "demo@bada.local"


def _demo_user(db: Session) -> User:
    u = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not u:
        u = User(email=DEMO_EMAIL, name="데모", preferred_lang="ko")
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def get_current_user(db: Session = Depends(get_db)) -> User:
    """현재 사용자.

    AWS 모드(인증 담당 구현 지점): Authorization 헤더의 Cognito JWT를 검증하고
    sub/email로 User를 upsert해 반환하도록 교체. 로컬 모드: 단일 데모 유저.
    """
    if settings.auth_mode == "cognito":
        raise NotImplementedError("Cognito JWT 검증 구현 (인증 담당)")
    return _demo_user(db)
