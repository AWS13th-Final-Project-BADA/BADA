"""인증 서비스 — JWT 발급/검증 + 소셜 OAuth(kakao/google/naver).

JWT는 외부 의존성 없이 표준 HS256으로 직접 구현(서명 검증 + 만료 확인).
소셜 로그인은 provider별 엔드포인트만 다르고 흐름은 동일:
  authorize_url → (사용자 동의) → exchange_code → get_userinfo → upsert
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

import requests

from ..config import settings

# provider별 OAuth 엔드포인트.
PROVIDERS: dict[str, dict[str, str]] = {
    "kakao": {
        "authorize": "https://kauth.kakao.com/oauth/authorize",
        "token": "https://kauth.kakao.com/oauth/token",
        "userinfo": "https://kapi.kakao.com/v2/user/me",
        "scope": "",
    },
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "naver": {
        "authorize": "https://nid.naver.com/oauth2.0/authorize",
        "token": "https://nid.naver.com/oauth2.0/token",
        "userinfo": "https://openapi.naver.com/v1/nid/me",
        "scope": "",
    },
}


def _conf(provider: str) -> dict[str, str]:
    """provider별 client_id/secret/redirect_uri 를 settings에서 가져옴."""
    if provider == "kakao":
        return {"client_id": settings.kakao_rest_api_key,
                "client_secret": settings.kakao_client_secret,
                "redirect_uri": settings.kakao_redirect_uri}
    if provider == "google":
        return {"client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri}
    if provider == "naver":
        return {"client_id": settings.naver_client_id,
                "client_secret": settings.naver_client_secret,
                "redirect_uri": settings.naver_redirect_uri}
    raise ValueError(f"unknown provider: {provider}")


def is_configured(provider: str) -> bool:
    c = _conf(provider)
    return bool(c["client_id"])


# ── JWT (HS256, 표준 호환) ──
def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_access_token(*, sub: str, email: str | None = None, name: str | None = None) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": sub, "email": email, "name": name,
               "iat": now, "exp": now + settings.jwt_expire_minutes * 60}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(settings.jwt_secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        h, p, s = token.split(".")
        expected = hmac.new(settings.jwt_secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(s)):
            return None
        payload = json.loads(_b64url_decode(p))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


# ── 소셜 OAuth (공통) ──
# 로그인 시 항상 '계정 선택/재인증'을 띄워 다른 계정으로도 로그인 가능하게.
_FORCE_SELECT = {
    "google": {"prompt": "select_account"},   # 구글 계정 선택 화면
    "kakao": {"prompt": "login"},              # 카카오 재로그인(다른 계정 입력 가능)
    "naver": {"auth_type": "reauthenticate"},  # 네이버 재인증
}


def authorize_url(provider: str, state: str) -> str:
    ep, c = PROVIDERS[provider], _conf(provider)
    params = {"client_id": c["client_id"], "redirect_uri": c["redirect_uri"],
              "response_type": "code", "state": state}
    if ep["scope"]:
        params["scope"] = ep["scope"]
    params.update(_FORCE_SELECT.get(provider, {}))
    return f"{ep['authorize']}?{urlencode(params)}"


def exchange_code(provider: str, code: str, state: str = "") -> str:
    ep, c = PROVIDERS[provider], _conf(provider)
    data = {"grant_type": "authorization_code", "client_id": c["client_id"],
            "redirect_uri": c["redirect_uri"], "code": code}
    if c["client_secret"]:
        data["client_secret"] = c["client_secret"]
    if provider == "naver":
        data["state"] = state
        r = requests.get(ep["token"], params=data, timeout=10)
    else:
        r = requests.post(ep["token"], data=data, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def get_userinfo(provider: str, access_token: str) -> dict[str, Any]:
    ep = PROVIDERS[provider]
    r = requests.get(ep["userinfo"], headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if provider == "kakao":
        acct = data.get("kakao_account", {}) or {}
        prof = acct.get("profile", {}) or {}
        return {"provider_id": str(data.get("id")), "email": acct.get("email"), "name": prof.get("nickname")}
    if provider == "google":
        return {"provider_id": str(data.get("sub")), "email": data.get("email"), "name": data.get("name")}
    if provider == "naver":
        resp = data.get("response", {}) or {}
        return {"provider_id": str(resp.get("id")), "email": resp.get("email"),
                "name": resp.get("name") or resp.get("nickname")}
    raise ValueError(f"unknown provider: {provider}")
