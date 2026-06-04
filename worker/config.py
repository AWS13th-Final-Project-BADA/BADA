"""Worker 설정 — provider 모드 선택.

PROVIDER_MODE=local  → Mock providers (AWS 없이 전부 동작, 기본값)
PROVIDER_MODE=aws    → 실제 Bedrock/Upstage(또는 Parseur)/Translate
STRUCTURED_ENGINE    → 정형문서 OCR 엔진 선택: upstage | parseur
"""
import os

PROVIDER_MODE = os.environ.get("PROVIDER_MODE", "local")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "")
PARSEUR_API_KEY = os.environ.get("PARSEUR_API_KEY", "")
STRUCTURED_ENGINE = os.environ.get("STRUCTURED_ENGINE", "upstage")  # upstage | parseur
