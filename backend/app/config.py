from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 로컬 기본: SQLite. Postgres로 바꾸려면 이 값만 교체.
    database_url: str = "sqlite:///./bada.db"

    # 동작 모드 (기능 담당자가 'aws'/'cognito'/'s3'로 전환)
    auth_mode: str = "demo"        # demo | cognito
    storage_mode: str = "local"    # local | s3
    upload_dir: str = "./uploads"

    aws_region: str = "ap-northeast-2"
    aws_profile: str = ""
    s3_bucket: str = ""
    kms_key_id: str = ""
    sqs_queue_url: str = ""
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_vision_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    ai_chat_mode: str = "mock"     # mock | bedrock
    ai_chat_max_tokens: int = 700
    upstage_api_key: str = ""
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    retention_days: int = 90


settings = Settings()
