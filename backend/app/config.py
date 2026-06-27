import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./bada.db"
    database_auto_create: bool = True
    database_ssl_mode: str = ""
    database_pool_size: int = 5
    database_max_overflow: int = 10

    provider_mode: str = "local"
    structured_engine: str = "vision"
    auth_mode: str = "demo"  # demo | oauth  (Cognito 제거됨 — 소셜 OAuth로 단일화)
    storage_mode: str = "local"  # local | s3
    upload_dir: str = "./uploads"

    aws_region: str = "ap-northeast-2"
    aws_profile: str = ""
    s3_bucket: str = ""
    kms_key_id: str = ""
    sqs_queue_url: str = ""
    transcription_dispatch_mode: str = "inline"  # inline | sqs
    transcribe_mode: str = ""

    bedrock_model_id: str = "global.anthropic.claude-sonnet-4-6"
    bedrock_vision_model_id: str = "global.anthropic.claude-sonnet-4-6"
    ai_chat_mode: str = "mock"
    ai_chat_max_tokens: int = 700

    rag_enabled: bool = True
    rag_use_vector: bool = True
    rag_top_k: int = 4
    rag_min_keyword_score: int = 1
    embedding_mode: str = "mock"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    embedding_dimension: int = 1024
    upstage_api_key: str = ""
    parseur_api_key: str = ""

    retention_days: int = 90

    auth_jwt_enabled: bool = True
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    app_base_url: str = "http://localhost:8000"

    kakao_rest_api_key: str = ""
    kakao_client_secret: str = ""
    kakao_redirect_uri: str = "http://localhost:8000/auth/kakao/callback"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    naver_client_id: str = ""
    naver_client_secret: str = ""
    naver_redirect_uri: str = "http://localhost:8000/auth/naver/callback"


settings = Settings()

os.environ.setdefault("PROVIDER_MODE", settings.provider_mode)
os.environ.setdefault("TRANSCRIBE_MODE", settings.transcribe_mode or settings.provider_mode)
os.environ.setdefault("STRUCTURED_ENGINE", settings.structured_engine)
os.environ.setdefault("AWS_REGION", settings.aws_region)
os.environ.setdefault("BEDROCK_MODEL_ID", settings.bedrock_model_id)
if settings.upstage_api_key:
    os.environ.setdefault("UPSTAGE_API_KEY", settings.upstage_api_key)
if settings.parseur_api_key:
    os.environ.setdefault("PARSEUR_API_KEY", settings.parseur_api_key)
