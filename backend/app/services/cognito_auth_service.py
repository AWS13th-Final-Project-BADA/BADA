from __future__ import annotations

import time
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import HTTPException
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User


class CognitoConfigError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(settings.cognito_user_pool_id and settings.cognito_client_id and settings.cognito_domain)


def authorize_url(state: str) -> str:
    _require_config()
    params = {
        "client_id": settings.cognito_client_id,
        "response_type": "code",
        "scope": settings.cognito_scopes,
        "redirect_uri": settings.cognito_redirect_uri,
        "state": state,
    }
    return f"{_domain()}/oauth2/authorize?{urlencode(params)}"


def logout_url() -> str:
    _require_config()
    params = {
        "client_id": settings.cognito_client_id,
        "logout_uri": settings.cognito_logout_uri,
    }
    return f"{_domain()}/logout?{urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    _require_config()
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.cognito_client_id,
        "code": code,
        "redirect_uri": settings.cognito_redirect_uri,
    }
    auth = HTTPBasicAuth(settings.cognito_client_id, settings.cognito_client_secret) if settings.cognito_client_secret else None
    response = requests.post(f"{_domain()}/oauth2/token", data=data, auth=auth, timeout=10)
    response.raise_for_status()
    return response.json()


def verify_cognito_token(token: str, *, allowed_token_uses: set[str] | None = None) -> dict[str, Any]:
    _require_config()
    allowed_token_uses = allowed_token_uses or {"access", "id"}

    try:
        import jwt
        from jwt import PyJWKClient
    except Exception as exc:  # pragma: no cover - depends on optional runtime package.
        raise HTTPException(status_code=500, detail="PyJWT[crypto] dependency is required for Cognito auth") from exc

    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        token_use = unverified.get("token_use")
        if token_use not in allowed_token_uses:
            raise HTTPException(status_code=401, detail="invalid Cognito token_use")
        if unverified.get("iss") != _issuer():
            raise HTTPException(status_code=401, detail="invalid Cognito issuer")

        signing_key = _jwk_client().get_signing_key_from_jwt(token).key
        if token_use == "id":
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=settings.cognito_client_id,
                issuer=_issuer(),
            )
        else:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=_issuer(),
                options={"verify_aud": False},
            )
            if payload.get("client_id") != settings.cognito_client_id:
                raise HTTPException(status_code=401, detail="invalid Cognito client_id")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid Cognito token") from exc

    return payload


def get_or_create_user_from_claims(db: Session, payload: dict[str, Any]) -> User:
    cognito_sub = payload.get("sub")
    if not cognito_sub:
        raise HTTPException(status_code=401, detail="Cognito token missing sub")

    user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
    if not user:
        email = _claim_str(payload, "email")
        if email:
            user = db.query(User).filter(User.email == email, User.cognito_sub.is_(None)).first()
            if user:
                user.cognito_sub = cognito_sub

    if not user:
        user = User(
            cognito_sub=cognito_sub,
            email=_claim_str(payload, "email"),
            name=_display_name(payload),
            provider="cognito",
            provider_id=cognito_sub,
            preferred_lang="ko",
        )
        db.add(user)
    else:
        _sync_user_from_claims(user, payload)

    db.commit()
    db.refresh(user)
    return user


def _sync_user_from_claims(user: User, payload: dict[str, Any]) -> None:
    email = _claim_str(payload, "email")
    name = _display_name(payload)
    if email and user.email != email:
        user.email = email
    if name and user.name != name:
        user.name = name
    user.provider = "cognito"
    user.provider_id = payload.get("sub")


def _display_name(payload: dict[str, Any]) -> str:
    name = _claim_str(payload, "name")
    if name:
        return name
    given = _claim_str(payload, "given_name")
    family = _claim_str(payload, "family_name")
    if given or family:
        return " ".join(part for part in [given, family] if part)
    username = _claim_str(payload, "cognito:username")
    if username:
        return username
    email = _claim_str(payload, "email")
    if email and "@" in email:
        return email.split("@", 1)[0]
    return "사용자"


def _claim_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return str(value).strip() if value else None


def _require_config() -> None:
    if not is_configured():
        raise CognitoConfigError("COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, and COGNITO_DOMAIN are required")


def _domain() -> str:
    return settings.cognito_domain.rstrip("/")


def _issuer() -> str:
    return f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}"


@lru_cache(maxsize=4)
def _jwk_client():
    import jwt

    return jwt.PyJWKClient(f"{_issuer()}/.well-known/jwks.json")
