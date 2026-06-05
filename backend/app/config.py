import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 는 항상 backend/.env 에서 읽는다 (uvicorn 실행 폴더와 무관하게 동작).
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # 로컬 기본: SQLite. Postgres로 바꾸려면 이 값만 교체.
    database_url: str = "sqlite:///./bada.db"

    # 동작 모드 (기능 담당자가 전환)
    #   provider_mode: local=Mock / aws=실제 OCR·AI·번역(Bedrock/Upstage/Translate)
    provider_mode: str = "local"
    structured_engine: str = "vision"    # 정형문서 OCR: vision(기본) | upstage | parseur
    auth_mode: str = "demo"        # demo | cognito
    storage_mode: str = "local"    # local | s3
    upload_dir: str = "./uploads"

    aws_region: str = "ap-northeast-2"
    aws_profile: str = ""
    s3_bucket: str = ""
    kms_key_id: str = ""
    sqs_queue_url: str = ""
    # Claude Sonnet 4.6 (Global 추론 프로파일, 비전 지원). 텍스트·비전 공용.
    bedrock_model_id: str = "global.anthropic.claude-sonnet-4-6"
    bedrock_vision_model_id: str = "global.anthropic.claude-sonnet-4-6"
    ai_chat_mode: str = "mock"     # mock | bedrock
    ai_chat_max_tokens: int = 700
    upstage_api_key: str = ""
    parseur_api_key: str = ""
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    retention_days: int = 90


settings = Settings()

# .env 설정을 worker(providers)가 읽는 환경변수로 브리지.
# → .env 한 곳에서 provider_mode=aws + 키만 넣으면 OCR·AI·번역이 실제로 전환됨.
os.environ.setdefault("PROVIDER_MODE", settings.provider_mode)
os.environ.setdefault("STRUCTURED_ENGINE", settings.structured_engine)
os.environ.setdefault("AWS_REGION", settings.aws_region)
os.environ.setdefault("BEDROCK_MODEL_ID", settings.bedrock_model_id)
if settings.upstage_api_key:
    os.environ.setdefault("UPSTAGE_API_KEY", settings.upstage_api_key)
if settings.parseur_api_key:
    os.environ.setdefault("PARSEUR_API_KEY", settings.parseur_api_key)
