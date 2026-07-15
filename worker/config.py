"""Worker 설정 — provider 모드 선택.

PROVIDER_MODE=local  → Mock providers (AWS 없이 전부 동작, 기본값)
PROVIDER_MODE=aws    → 실제 Bedrock/Upstage/Translate

개별 기능별 모드 오버라이드:
TRANSLATE_MODE=aws → 번역만 실제 Amazon Translate 사용 (나머지는 PROVIDER_MODE 따름)
TRANSCRIBE_MODE=aws → 음성 전사만 실제 Amazon Transcribe 사용 (나머지는 PROVIDER_MODE 따름)
STRUCTURED_ENGINE  → 정형문서 OCR 엔진: vision(기본) | upstage | parseur
                     vision = 전부 Claude Vision(다국어·숫자·손글씨 강함, 엔진 1개).
                     upstage/parseur = 정형문서만 해당 엔진으로(표 정밀이 필요할 때, 키 있어야 함).
"""
import os

PROVIDER_MODE = os.environ.get("PROVIDER_MODE", "local")
TRANSLATE_MODE = os.environ.get("TRANSLATE_MODE", PROVIDER_MODE)  # 번역 전용 모드 오버라이드
TRANSCRIBE_MODE = os.environ.get("TRANSCRIBE_MODE", PROVIDER_MODE)  # 음성 전사 전용 모드 오버라이드
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "")
PARSEUR_API_KEY = os.environ.get("PARSEUR_API_KEY", "")
STRUCTURED_ENGINE = os.environ.get("STRUCTURED_ENGINE", "vision")  # vision | upstage | parseur
