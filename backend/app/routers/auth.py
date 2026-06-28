"""Authentication routes for social OAuth login (Google/Kakao/Naver) and JWT user lookup."""
from __future__ import annotations

import base64
import json
import secrets
import string
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
_PROVIDERS = ("kakao", "google", "naver")


def _safe_return_to(value: str | None) -> str | None:
    """Whitelist app/web callback targets so OAuth state cannot become an open redirect."""
    if not value or len(value) > 800:
        return None

    parsed = urlsplit(value)
    if parsed.scheme in {"bada", "exp"}:
        return value

    if parsed.scheme in {"http", "https"} and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "badasoft.com",
        "www.badasoft.com",
        "api.badasoft.com",
    }:
        return value

    return None


def _encode_state(return_to: str | None = None) -> str:
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "return_to": _safe_return_to(return_to),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_state_return_to(state: str) -> str | None:
    if not state:
        return None
    try:
        padded = state + ("=" * (-len(state) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    return _safe_return_to(payload.get("return_to"))


def _append_token_query(url: str, token: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["token"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _redirect_with_token(token: str, state: str = "") -> RedirectResponse:
    return_to = _decode_state_return_to(state)
    if return_to:
        return RedirectResponse(_append_token_query(return_to, token))

    app_base_url = settings.app_base_url.rstrip("/")
    return RedirectResponse(f"{app_base_url}/#token={token}")


@router.get("/{provider}/login")
def social_login(provider: str, redirect_uri: str | None = None):
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=404, detail="Unsupported login provider")
    if not auth_service.is_configured(provider):
        raise HTTPException(status_code=503, detail=f"{provider} login is not configured")

    state = _encode_state(redirect_uri)
    return RedirectResponse(auth_service.authorize_url(provider, state))


@router.get("/{provider}/callback")
def social_callback(
    provider: str,
    code: str | None = None,
    state: str = "",
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
):
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=404, detail="Unsupported login provider")
    if error or error_description:
        raise HTTPException(status_code=400, detail=f"{provider} authorization rejected: {error} / {error_description}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    access_token = auth_service.exchange_code(provider, code, state)
    info = auth_service.get_userinfo(provider, access_token)
    user = _upsert_social_user(
        db,
        provider=provider,
        provider_id=info["provider_id"],
        email=info.get("email"),
        name=info.get("name"),
    )

    jwt = auth_service.create_access_token(sub=user.id, email=user.email, name=user.name)
    return _redirect_with_token(jwt, state)


@router.post("/kakao/link-code")
def kakao_link_code(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Issue a short code so a logged-in user can link the Kakao channel."""
    from ..models import KakaoLinkCode

    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(chars) for _ in range(6))
        if any(ch.isdigit() for ch in code) and any(ch.isalpha() for ch in code):
            break

    db.add(KakaoLinkCode(code=code, user_id=user.id))
    db.commit()
    return {"code": code, "guide": "Send this code to the BADA Kakao channel to link your account."}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "preferred_lang": user.preferred_lang,
        "provider": user.provider,
    }


@router.post("/logout")
def logout():
    return {"ok": True}


def _upsert_social_user(
    db: Session,
    *,
    provider: str,
    provider_id: str,
    email: str | None,
    name: str | None,
) -> User:
    # 1) (provider, provider_id)로 기존 유저 조회 — 기존 동작 유지
    user = db.query(User).filter(User.provider == provider, User.provider_id == provider_id).first()
    if user:
        if name and user.name != name:
            user.name = name
            db.commit()
        return user

    # 2) 같은 이메일이 이미 있으면(다른 provider로 먼저 가입 등) 그 계정에 연결.
    #    email이 있을 때만 — 카카오/네이버는 이메일 미동의 시 None일 수 있음.
    if email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.provider = provider
            existing.provider_id = provider_id
            if name and existing.name != name:
                existing.name = name
            db.commit()
            return existing

    # 3) 신규 생성 — 기존 동작 유지 + 동시 로그인 레이스 안전망
    user = User(
        provider=provider,
        provider_id=provider_id,
        email=email,
        name=name or "User",
        preferred_lang="ko",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.query(User).filter(User.provider == provider, User.provider_id == provider_id).first()
        if user is None and email:
            user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise
        return user
    db.refresh(user)
    return user
