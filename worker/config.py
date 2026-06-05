"""Worker 설정 — provider 모드 선택.

PROVIDER_MODE=local  → Mock providers (AWS 없이 전부 동작, 기본값)
PROVIDER_MODE=aws    → 실제 Bedrock/Upstage/Translate (각 기능 담당자가 구현)

개별 기능별 모드 오버라이드:
TRANSLATE_MODE=aws → 번역만 실제 Amazon Translate 사용 (나머지는 PROVIDER_MODE 따름)
"""
import os

PROVIDER_MODE = os.environ.get("PROVIDER_MODE", "local")
TRANSLATE_MODE = os.environ.get("TRANSLATE_MODE", PROVIDER_MODE)  # 번역 전용 모드 오버라이드
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "")
