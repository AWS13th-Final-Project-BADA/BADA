"""인증 라우터 — 카카오 소셜 로그인 + JWT.

흐름:
  GET /auth/kakao/login     → 카카오 인증 페이지로 리다이렉트
  GET /auth/kakao/callback  → code 교환 → 사용자 조회 → User upsert → JWT 발급 → 프론트로 리다이렉트(#token=...)
  GET /auth/me              → 현재 로그인 사용자(JWT 필요)
  POST /auth/logout         → JWT는 서버 상태 없음. 프론트가 토큰 삭제(여기선 ok만 반환)
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/kakao/login")
def kakao_login():
    if not settings.kakao_rest_api_key:
        raise HTTPException(status_code=503, detail="카카오 로그인 미설정(KAKAO_REST_API_KEY)")
    state = secrets.token_urlsafe(16)
    return RedirectResponse(auth_service.kakao_authorize_url(state))


@router.get("/kakao/callback")
def kakao_callback(request: Request, code: str | None = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="code 누락")

    token = auth_service.kakao_exchange_code(code)
    info = auth_service.kakao_get_userinfo(token["access_token"])
    user = _upsert_social_user(db, provider="kakao", provider_id=info["provider_id"],
                               email=info.get("email"), name=info.get("name"))

    jwt = auth_service.create_access_token(sub=user.id, email=user.email, name=user.name)
    # 프론트로 토큰 전달(URL fragment → 서버 로그에 안 남음).
    return RedirectResponse(f"{settings.app_base_url}/#token={jwt}")


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name,
            "preferred_lang": user.preferred_lang}


@router.post("/logout")
def logout():
    return {"ok": True}


def _upsert_social_user(db: Session, *, provider: str, provider_id: str,
                        email: str | None, name: str | None) -> User:
    user = (
        db.query(User)
        .filter(User.provider == provider, User.provider_id == provider_id)
        .first()
    )
    if user:
        if name and user.name != name:
            user.name = name
            db.commit()
        return user
    user = User(provider=provider, provider_id=provider_id, email=email,
                name=name or "사용자", preferred_lang="ko")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
