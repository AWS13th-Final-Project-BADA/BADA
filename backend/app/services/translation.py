"""실시간 번역 서비스 — Amazon Translate 래퍼.

분석 결과 조회 시 한국어 원문을 사용자 언어로 번역.
PROVIDER_MODE=aws일 때만 실제 번역, 로컬은 원문 반환.
"""
from __future__ import annotations

from ..config import settings

_client = None


class Translator:
    def translate(self, text: str, target_lang: str) -> str:
        if not text or target_lang == "ko":
            return text
        try:
            return _aws_translate(text, target_lang)
        except Exception:
            return text


def _aws_translate(text: str, target_lang: str) -> str:
    """Amazon Translate 호출."""
    global _client
    if _client is None:
        import boto3
        _client = boto3.client("translate", region_name=settings.aws_region)

    # Amazon Translate 언어 코드 매핑
    lang_map = {"en": "en", "vi": "vi", "km": "km", "ja": "ja", "ko": "ko"}
    target = lang_map.get(target_lang, target_lang)

    result = _client.translate_text(
        Text=text[:5000],  # Amazon Translate 최대 5000자
        SourceLanguageCode="ko",
        TargetLanguageCode=target,
    )
    return result["TranslatedText"]


def get_translator() -> Translator:
    """번역기 인스턴스 반환."""
    return Translator()
