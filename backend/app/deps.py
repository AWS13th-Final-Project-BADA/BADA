"""공통 의존성 — 인증. 모든 라우터가 같은 seam을 쓴다.

우선순위:
  1) Authorization: Bearer <JWT>  → JWT 검증 후 해당 User 반환 (소셜 로그인)
  2) 토큰 없음 + demo 모드        → 단일 데모 유저 (기존 동작 유지, 점진적 전환)
교체/확장 지점은 `get_current_user` 한 곳뿐 — 라우터는 건드리지 않는다.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User
from .services import auth_service

DEMO_EMAIL = "demo@bada.local"


def _demo_user(db: Session) -> User:
    u = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if not u:
        u = User(email=DEMO_EMAIL, name="데모", preferred_lang="ko")
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _user_from_bearer(db: Session, authorization: str | None) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = auth_service.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자 없음")
    return user


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    if settings.auth_jwt_enabled:
        user = _user_from_bearer(db, authorization)
        if user:
            return user
    if settings.auth_mode == "demo":
        return _demo_user(db)  # 로컬 개발/테스트 전용
    raise HTTPException(status_code=401, detail="login required")
