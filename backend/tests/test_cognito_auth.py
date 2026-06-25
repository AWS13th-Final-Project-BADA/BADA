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
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_client_secret", "")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_domain", "https://bada.auth.ap-northeast-2.amazoncognito.com")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_redirect_uri", "http://localhost:8000/auth/cognito/callback")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_logout_uri", "http://localhost:8000/")
    monkeypatch.setattr(cognito_auth_service.settings, "cognito_scopes", "openid email profile")
    monkeypatch.setattr(cognito_auth_service.settings, "app_base_url", "http://localhost:8000")


def test_cognito_authorize_url_uses_hosted_ui(monkeypatch):
    configure_cognito(monkeypatch)

    url = cognito_auth_service.authorize_url("state-1")

    assert url.startswith("https://bada.auth.ap-northeast-2.amazoncognito.com/oauth2/authorize?")
    assert "client_id=client123" in url
    assert "response_type=code" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcognito%2Fcallback" in url
    assert "state=state-1" in url


def test_cognito_authorize_url_can_force_google_account_selection(monkeypatch):
    configure_cognito(monkeypatch)

    url = cognito_auth_service.authorize_url("state-1", identity_provider="Google", prompt="select_account")

    assert "identity_provider=Google" in url
    assert "prompt=select_account" in url


def test_cognito_logout_url_can_override_logout_uri(monkeypatch):
    configure_cognito(monkeypatch)

    url = cognito_auth_service.logout_url("bada://auth")

    assert "logout_uri=bada%3A%2F%2Fauth" in url


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
    existing = User(email="same@example.com", name="Existing User", preferred_lang="ko")
    db.add(existing)
    db.commit()

    user = cognito_auth_service.get_or_create_user_from_claims(
        db,
        {
            "sub": "cognito-sub-2",
            "email": "same@example.com",
            "name": "New Name",
        },
    )

    assert user.id == existing.id
    assert user.cognito_sub == "cognito-sub-2"
    assert user.name == "New Name"
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


def test_auth_state_preserves_mobile_return_to():
    from app.routers import auth as auth_router

    state = auth_router._encode_state("bada://auth")

    assert auth_router._decode_state_return_to(state) == "bada://auth"


def test_auth_state_rejects_unknown_return_to():
    from app.routers import auth as auth_router

    state = auth_router._encode_state("https://evil.example/callback")

    assert auth_router._decode_state_return_to(state) is None


def test_cognito_callback_redirects_token_to_mobile_deep_link(client, monkeypatch):
    from app.routers import auth as auth_router

    configure_cognito(monkeypatch)
    state = auth_router._encode_state("bada://auth")
    monkeypatch.setattr(cognito_auth_service, "exchange_code", lambda code: {"id_token": "id-token-123"})
    monkeypatch.setattr(
        cognito_auth_service,
        "verify_cognito_token",
        lambda token: {"sub": "sub-1", "email": "worker@example.com", "name": "Worker"},
    )
    monkeypatch.setattr(cognito_auth_service, "get_or_create_user_from_claims", lambda db, payload: User(id="u1"))

    res = client.get(f"/auth/cognito/callback?code=ok&state={state}", follow_redirects=False)

    assert res.status_code in {302, 307}
    assert res.headers["location"] == "bada://auth?token=id-token-123"


def test_cognito_callback_falls_back_to_web_hash_redirect(client, monkeypatch):
    configure_cognito(monkeypatch)
    monkeypatch.setattr(cognito_auth_service, "exchange_code", lambda code: {"id_token": "id-token-456"})
    monkeypatch.setattr(
        cognito_auth_service,
        "verify_cognito_token",
        lambda token: {"sub": "sub-2", "email": "worker2@example.com", "name": "Worker Two"},
    )
    monkeypatch.setattr(cognito_auth_service, "get_or_create_user_from_claims", lambda db, payload: User(id="u2"))

    res = client.get("/auth/cognito/callback?code=ok&state=legacy-state", follow_redirects=False)

    assert res.status_code in {302, 307}
    assert res.headers["location"] == "http://localhost:8000/#token=id-token-456"
