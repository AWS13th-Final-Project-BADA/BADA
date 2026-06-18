from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import User
from app.services import cognito_auth_service


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def configure_cognito(monkeypatch):
    monkeypatch.setattr(cognito_auth_service.settings, "aws_region", "ap-northeast-2")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_user_pool_id", "ap-northeast-2_pool")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_client_id", "client123")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_domain", "https://bada.auth.ap-northeast-2.amazoncognito.com")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_redirect_uri", "http://localhost:8000/auth/cognito/callback")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_logout_uri", "http://localhost:8000/")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_scopes", "openid email profile")


def test_cognito_authorize_url_uses_hosted_ui(monkeypatch):
    configure_cognito(monkeypatch)

    url = cognito_auth_service.authorize_url("state-1")

    assert url.startswith("https://bada.auth.ap-northeast-2.amazoncognito.com/oauth2/authorize?")
    assert "client_id=client123" in url
    assert "response_type=code" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcognito%2Fcallback" in url
    assert "state=state-1" in url


def test_cognito_claims_create_user():
    db = make_db()

    user = cognito_auth_service.get_or_create_user_from_claims(
        db,
        {
            "sub": "cognito-sub-1",
            "email": "worker@example.com",
            "name": "BADA Worker",
        },
    )

    assert user.cognito_sub == "cognito-sub-1"
    assert user.email == "worker@example.com"
    assert user.name == "BADA Worker"
    assert user.provider == "cognito"


def test_cognito_claims_attach_existing_email_user():
    db = make_db()
    existing = User(email="same@example.com", name="기존 사용자", preferred_lang="ko")
    db.add(existing)
    db.commit()

    user = cognito_auth_service.get_or_create_user_from_claims(
        db,
        {
            "sub": "cognito-sub-2",
            "email": "same@example.com",
            "name": "새 이름",
        },
    )

    assert user.id == existing.id
    assert user.cognito_sub == "cognito-sub-2"
    assert user.name == "새 이름"
    assert user.provider == "cognito"


def test_get_current_user_uses_cognito_when_auth_mode_is_cognito(monkeypatch):
    from app import deps

    db = make_db()
    monkeypatch.setattr(deps.settings, "auth_mode", "cognito")
    monkeypatch.setattr(
        deps.cognito_auth_service,
        "verify_cognito_token",
        lambda token: {"sub": "cognito-sub-3", "email": "claim@example.com", "name": "Claim User"},
    )

    user = deps.get_current_user(db=db, authorization="Bearer fake-cognito-token")

    assert user.cognito_sub == "cognito-sub-3"
    assert user.email == "claim@example.com"
    assert user.name == "Claim User"
