"""Translate provider — 번역만. 원문은 항상 보존(병기)된다.

local=Mock(원문 유지), aws=Amazon Translate(실제 호출). 전환은 PROVIDER_MODE.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config import AWS_REGION, PROVIDER_MODE


class Translator(ABC):
    @abstractmethod
    def translate(self, text: str, target_lang: str) -> str: ...


class MockTranslator(Translator):
    """로컬 기본값. 항등(원문 그대로) — 원문 병기 원칙상 안전한 폴백."""

    def translate(self, text: str, target_lang: str) -> str:
        return text


class AmazonTranslator(Translator):
    """Amazon Translate 실제 호출. 소스는 한국어 기준(필요 시 자동 감지)."""

    _client = None

    def _c(self):
        if AmazonTranslator._client is None:
            import boto3  # 지연 임포트
            AmazonTranslator._client = boto3.client("translate", region_name=AWS_REGION)
        return AmazonTranslator._client

    def translate(self, text: str, target_lang: str) -> str:
        if not text or target_lang == "ko":
            return text
        r = self._c().translate_text(Text=text, SourceLanguageCode="ko", TargetLanguageCode=target_lang)
        return r["TranslatedText"]


def get_translator() -> Translator:
    return AmazonTranslator() if PROVIDER_MODE == "aws" else MockTranslator()
