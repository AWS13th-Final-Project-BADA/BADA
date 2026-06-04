"""Translate provider — 번역만. 원문은 항상 보존(병기)된다.

담당: 다국어 기능. `AmazonTranslate.translate` 채우면 끝.
크메르/네팔 품질 이슈는 ko->en->km 피벗으로 보완(담당자 결정, tech.md).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from config import PROVIDER_MODE


class Translator(ABC):
    @abstractmethod
    def translate(self, text: str, target_lang: str) -> str:
        ...


class MockTranslator(Translator):
    """로컬 기본값. 항등 변환(원문 그대로) — 원문 병기 원칙상 안전한 폴백."""

    def translate(self, text: str, target_lang: str) -> str:
        if target_lang == "ko" or not text:
            return text
        return text  # 실제 번역은 AmazonTranslate에서. 로컬은 원문 유지.


class AmazonTranslator(Translator):
    """담당자 구현 지점."""

    def __init__(self):
        import boto3  # 지연 임포트
        self.client = boto3.client("translate")

    def translate(self, text: str, target_lang: str) -> str:  # pragma: no cover
        raise NotImplementedError("Amazon Translate 호출 구현")


def get_translator() -> Translator:
    return AmazonTranslator() if PROVIDER_MODE == "aws" else MockTranslator()
