"""Worker 설정 — provider 모드 선택.

PROVIDER_MODE=local  → Mock providers (AWS 없이 전부 동작, 기본값)
PROVIDER_MODE=aws    → 실제 Bedrock/Upstage/Translate
STRUCTURED_ENGINE    → 정형문서 OCR 엔진: vision(기본) | upstage | parseur
                       vision = 전부 Claude Vision(다국어·숫자·손글씨 강함, 엔진 1개).
                       upstage/parseur = 정형문서만 해당 엔진으로(표 정밀이 필요할 때, 키 있어야 함).
"""
import os

PROVIDER_MODE = os.environ.get("PROVIDER_MODE", "local")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthro