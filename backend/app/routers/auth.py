"""인증 라우터 — 소셜 로그인(kakao/google/naver) + JWT.

  GET  /auth/{provider}/login     → 해당 provider 인증 페이지로 리다이렉트
  GET  /auth/{provider}/callback  → code 교환 → 사용자 조회 → User upsert → JWT → 프론트로(#token=)
  GET  /auth/me                   → 현재 로그인 사용자(JWT 필요)
  POST /auth/logout               → JWT는 서버 상태 없음(프론트가 토큰 삭제)
"""
from __future__ import annotations

import secrets
import string

import requests

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..services import auth_service, cognito_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
_PROVIDERS = ("kakao", "google", "naver")


@router.get("/cognito/login")
def cognito_login(identity_provider: str | None = None, prompt: str | None = None):
    if not cognito_auth_service.is_configured():
        raise HTTPException(status_code=503, detail="Cognito 로그인 미설정")
    state = secrets.token_urlsafe(16)
    return RedirectResponse(cognito_auth_service.authorize_url(state, identity_provider=identity_provider, prompt=prompt))


@router.get("/cognito/callback")
def cognito_callback(
    code: str | None = None,
    state: str = "",
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
):
    _ = state
    if error or error_description:
        raise HTTPException(status_code=400, detail=f"Cognito 인증 거부: {error} / {error_description}")
    if not code:
        raise HTTPException(status_code=400, detail="code 누락(Cognito에서 돌아오지 못함)")
    try:
        tokens = cognito_auth_service.exchange_code(code)
        token = tokens.get("id_token") or tokens.get("access_token")
        if not token:
            raise HTTPException(status_code=502, detail="Cognito token 응답 누락")
        payload = cognito_auth_service.verify_cognito_token(token)
        cognito_auth_service.get_or_create_user_from_claims(db, payload)
    except cognito_auth_service.CognitoConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Cognito token 교환 실패: {exc.response.text}") from exc

    app_base_url = settings.app_base_url.rstrip("/")
    return RedirectResponse(f"{app_base_url}/#token={token}")


@router.get("/cognito/logout")
def cognito_logout():
    if not cognito_auth_service.is_configured():
        app_base_url = settings.app_base_url.rstrip("/")
        return RedirectResponse(app_base_url)
    return RedirectResponse(cognito_auth_service.logout_url())


@router.get("/{provider}/login")
def social_login(provider: str):
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=404, detail="지원하지 않는 로그인 방식")
    if not auth_service.is_configured(provider):
        raise HTTPException(status_code=503, detail=f"{provider} 로그인 미설정(키 없음)")
    state = secrets.token_urlsafe(16)
    return RedirectResponse(auth_service.authorize_url(provider, state))


@router.get("/{provider}/callback")
def social_callback(provider: str, request: Request, code: str | None = None,
                    state: str = "", error: str | None = None,
                    error_description: str | None = None, db: Session = Depends(get_db)):
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=404, detail="지원하지 않는 로그인 방식")
    if error or error_description:
        # 카카오/구글/네이버가 code 대신 에러를 보낸 경우 그대로 노출(디버깅).
        raise HTTPException(status_code=400, detail=f"{provider} 인증 거부: {error} / {error_description}")
    if not code:
        raise HTTPException(status_code=400, detail="code 누락(인증 페이지에서 돌아오지 못함)")

    access_token = auth_service.exchange_code(provider, code, state)
    info = auth_service.get_userinfo(provider, access_token)
    user = _upsert_social_user(db, provider=provider, provider_id=info["provider_id"],
                               email=info.get("email"), name=info.get("name"))

    jwt = auth_service.create_access_token(sub=user.id, email=user.email, name=user.name)
    app_base_url = settings.app_base_url.rstrip("/")
    return RedirectResponse(f"{app_base_url}/#token={jwt}")


@router.post("/kakao/link-code")
def kakao_link_code(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """로그인한 사용자가 카카오 봇 연동용 6자리 코드를 발급받는다. (앱에서 호출)"""
    from ..models import KakaoLinkCode
    chars = string.ascii_uppercase + string.digits
    while True:   # 영문+숫자 혼합 보장(영어단어 오인 방지)
        code = "".join(secrets.choice(chars) for _ in range(6))
        if any(ch.isdigit() for ch in code) and any(ch.isalpha() for ch in code):
            break
    db.add(KakaoLinkCode(code=code, user_id=user.id))
    db.commit()
    return {"code": code, "guide": "카카오톡 BADA 채널에 이 코드를 보내면 계정이 연동돼요."}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name,
            "preferred_lang": user.preferred_lang, "provider": user.provider}


@router.post("/logout")
def logout():
    return {"ok": True}


def _upsert_social_user(db: Session, *, provider: str, provider_id: str,
                        email: str | None, name: str | None) -> User:
    user = (db.query(User)
            .filter(User.provider == provider, User.provider_id == provider_id)
            .first())
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
