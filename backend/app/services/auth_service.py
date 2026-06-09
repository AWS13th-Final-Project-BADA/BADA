"""인증 서비스 — JWT 발급/검증 + 카카오 OAuth.

JWT는 외부 의존성 없이 표준 HS256으로 직접 구현(서명 검증 + 만료 확인).
카카오 토큰 교환·사용자 조회는 requests 사용.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import requests

from ..config import settings

_KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
_KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"


# ── JWT (HS256, 표준 호환) ──
def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def create_access_token(*, sub: str, email: str | None = None, name: str | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
    }
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        h, p, s = token.split(".")
        signing_input = f"{h}.{p}".encode()
        expected = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(s)):
            return None
        payload = json.loads(_b64url_decode(p))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None  # 만료
        return payload
    except Exception:
        return None


# ── 카카오 OAuth ──
def kakao_authorize_url(state: str) -> str:
    from urllib.parse import urlencode

    params = {
        "client_id": settings.kakao_rest_api_key,
        "redirect_uri": settings.kakao_redirect_uri,
        "response_type": "code",
        "state": state,
    }
    return f"{_KAKAO_AUTH_URL}?{urlencode(params)}"


def kakao_exchange_code(code: str) -> dict[str, Any]:
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.kakao_rest_api_key,
        "redirect_uri": settings.kakao_redirect_uri,
        "code": code,
    }
    if settings.kakao_client_secret:
        data["client_secret"] = settings.kakao_client_secret
    r = requests.post(_KAKAO_TOKEN_URL, data=data, timeout=10)
    r.raise_for_status()
    return r.json()


def kakao_get_userinfo(access_token: str) -> dict[str, Any]:
    r = requests.get(
        _KAKAO_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    account = data.get("kakao_account", {}) or {}
    profile = account.get("profile", {}) or {}
    return {
        "provider_id": str(data.get("id")),
        "email": account.get("email"),
        "name": profile.get("nickname"),
    }
