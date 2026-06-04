"""Translate provider — 번역만. 원문은 항상 보존(병기)된다.

담당: 다국어 기능. AmazonTranslator가 Amazon Translate API를 캡슐화하고,
언어별 번역 전략(직접/피벗/보정)을 결정한다.
크메르/네팔 품질 이슈는 ko→en→target 피벗 + Claude 보정으로 보완.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from config import AWS_REGION, BEDROCK_MODEL_ID, PROVIDER_MODE
from providers.language_config import (
    SUPPORTED_LANGUAGES,
    UnsupportedLanguageError,
    get_language_strategy,
)

logger = logging.getLogger(__name__)


class Translator(ABC):
    @abstractmethod
    def translate(self, text: str, target_lang: str) -> str:
        ...

    @abstractmethod
    def translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        """Batch translate texts. Preserves order and length.

        Returns a list of same length as input where the i-th output
        corresponds to the i-th input. Failed items return source text.
        """
        ...


class MockTranslator(Translator):
    """로컬 기본값. 항등 변환(원문 그대로) — 원문 병기 원칙상 안전한 폴백."""

    def translate(self, text: str, target_lang: str) -> str:
        if target_lang == "ko" or not text:
            return text
        return text  # 실제 번역은 AmazonTranslator에서. 로컬은 원문 유지.

    def translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        if target_lang == "ko":
            return texts
        return [self.translate(t, target_lang) for t in texts]


class AmazonTranslator(Translator):
    """Amazon Translate API와의 통신을 캡슐화하고, 언어별 번역 전략을 결정한다.

    전략:
    - direct: ko→target (vi, en, id)
    - pivot+refine: ko→en→target + Claude 보정 (km, ne)

    오류 시 원문을 반환하여 시스템 중단을 방지한다 (graceful degradation).
    UnsupportedLanguageError는 catch하지 않고 전파한다.
    """

    # Korean sentence-ending markers (with trailing space for clean splits)
    _SENTENCE_MARKERS = ("습니다. ", "니다. ", "요. ", "다. ")

    def __init__(self, region: str = "ap-northeast-2"):
        import boto3  # 지연 임포트

        self._region = region
        self.client = boto3.client("translate", region_name=region)
        self._bedrock_client = None  # 지연 초기화 (refinement 시에만 생성)

    @staticmethod
    def _chunk_text(text: str, max_bytes: int = 10000) -> list[str]:
        """긴 텍스트를 max_bytes 이하 청크로 분할한다.

        한국어 문장 종결 마커(습니다. , 니다. , 요. , 다. ) 기준으로 분할하며,
        문장 경계를 찾을 수 없으면 마지막 공백 위치에서 분할한다.

        Args:
            text: 분할할 텍스트
            max_bytes: 청크당 최대 바이트 수 (기본 10000)

        Returns:
            분할된 텍스트 청크 리스트. 짧은 텍스트는 단일 요소 리스트 반환.
        """
        if len(text.encode("utf-8")) <= max_bytes:
            return [text]

        chunks: list[str] = []
        remaining = text

        while remaining:
            encoded = remaining.encode("utf-8")
            if len(encoded) <= max_bytes:
                chunks.append(remaining)
                break

            # Find the best split point within max_bytes
            # Decode the first max_bytes portion (may truncate multi-byte chars)
            candidate = encoded[:max_bytes].decode("utf-8", errors="ignore")

            # Try to find sentence boundary markers (search from end)
            best_pos = -1
            for marker in AmazonTranslator._SENTENCE_MARKERS:
                pos = candidate.rfind(marker)
                if pos != -1:
                    # Include the marker in this chunk
                    end_pos = pos + len(marker)
                    if end_pos > best_pos:
                        best_pos = end_pos

            if best_pos > 0:
                chunks.append(remaining[:best_pos])
                remaining = remaining[best_pos:]
            else:
                # No sentence boundary found — split at last space
                last_space = candidate.rfind(" ")
                if last_space > 0:
                    chunks.append(remaining[:last_space + 1])
                    remaining = remaining[last_space + 1:]
                else:
                    # No space either — force split at character boundary
                    chunks.append(candidate)
                    remaining = remaining[len(candidate):]

        return chunks

    def translate(self, text: str, target_lang: str) -> str:
        """한국어 텍스트를 target_lang으로 번역한다.

        10KB를 초과하는 텍스트는 문장 경계 기준으로 청크 분할 후
        개별 번역하여 결합한다.

        Args:
            text: 번역할 한국어 원문
            target_lang: 대상 언어 코드 (BADA 내부 코드)

        Returns:
            번역된 텍스트. 실패 시 원문 반환.

        Raises:
            UnsupportedLanguageError: target_lang이 SUPPORTED_LANGUAGES에 없는 경우
        """
        # No-op: 빈 텍스트
        if not text:
            return ""

        # target_lang 유효성 검증 — UnsupportedLanguageError는 전파
        strategy = get_language_strategy(target_lang)

        # No-op: 한국어 타겟이면 원문 그대로 반환
        if target_lang == "ko":
            return text

        # Chunking: 10KB 초과 시 분할 번역
        if len(text.encode("utf-8")) > 10000:
            return self._translate_chunked(text, target_lang, strategy)

        try:
            if strategy.strategy == "direct":
                return self._translate_direct(text, strategy.translate_code)

            elif strategy.strategy == "pivot+refine":
                return self._translate_pivot_refine(
                    text, strategy.translate_code, strategy.pivot_lang or "en"
                )

            else:
                # "none" 전략이지만 ko가 아닌 경우 (있을 수 없지만 방어)
                return text

        except UnsupportedLanguageError:
            raise
        except Exception as e:
            logger.warning(
                "Translation failed for target_lang=%s: %s. Returning source text.",
                target_lang,
                str(e),
            )
            return text

    def _translate_chunked(self, text: str, target_lang: str, strategy) -> str:
        """청크 분할 후 개별 번역하여 결합한다.

        각 청크가 실패하면 해당 청크의 원문을 사용하고 나머지는 계속 처리한다.
        """
        chunks = self._chunk_text(text)
        translated_chunks: list[str] = []

        for chunk in chunks:
            try:
                if strategy.strategy == "direct":
                    translated = self._translate_direct(chunk, strategy.translate_code)
                elif strategy.strategy == "pivot+refine":
                    translated = self._translate_pivot_refine(
                        chunk, strategy.translate_code, strategy.pivot_lang or "en"
                    )
                else:
                    translated = chunk
                translated_chunks.append(translated)
            except Exception as e:
                logger.warning(
                    "Chunk translation failed for target_lang=%s: %s. Using source chunk.",
                    target_lang,
                    str(e),
                )
                translated_chunks.append(chunk)

        return "".join(translated_chunks)

    def translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        """배치 번역: 리스트의 각 텍스트를 target_lang으로 번역한다.

        Args:
            texts: 번역할 한국어 원문 리스트
            target_lang: 대상 언어 코드 (BADA 내부 코드)

        Returns:
            번역된 텍스트 리스트. 길이와 순서가 입력과 동일.
            개별 항목 실패 시 해당 항목은 원문 반환.

        Raises:
            UnsupportedLanguageError: target_lang이 SUPPORTED_LANGUAGES에 없는 경우
        """
        # target_lang 유효성 검증 — UnsupportedLanguageError는 전파
        get_language_strategy(target_lang)

        # Short-circuit: 한국어 타겟이면 입력 그대로 반환
        if target_lang == "ko":
            return texts

        results: list[str] = []
        for text in texts:
            try:
                translated = self.translate(text, target_lang)
                results.append(translated)
            except UnsupportedLanguageError:
                raise
            except Exception as e:
                logger.warning(
                    "Batch item translation failed for target_lang=%s: %s. Using source text.",
                    target_lang,
                    str(e),
                )
                results.append(text)
        return results

    def _translate_direct(self, text: str, target_code: str) -> str:
        """직접 번역: ko→target (Amazon Translate 단일 호출)."""
        response = self.client.translate_text(
            Text=text,
            SourceLanguageCode="ko",
            TargetLanguageCode=target_code,
        )
        return response["TranslatedText"]

    def _translate_pivot_refine(
        self, text: str, target_code: str, pivot_lang: str
    ) -> str:
        """피벗+보정 번역: ko→en→target + Claude refinement.

        1. ko→en (Amazon Translate)
        2. en→target (Amazon Translate)
        3. Claude 보정 (실패 시 2단계 결과를 그대로 사용)
        """
        # Step 1: ko → en (pivot)
        en_response = self.client.translate_text(
            Text=text,
            SourceLanguageCode="ko",
            TargetLanguageCode=pivot_lang,
        )
        english_text = en_response["TranslatedText"]

        # Step 2: en → target
        target_response = self.client.translate_text(
            Text=english_text,
            SourceLanguageCode=pivot_lang,
            TargetLanguageCode=target_code,
        )
        draft = target_response["TranslatedText"]

        # Step 3: Claude refinement (fallback to draft on failure)
        return self._refine_with_claude(text, draft, target_code)

    def _get_bedrock_client(self):
        """Bedrock 클라이언트를 지연 생성하고 캐시한다.

        translate.py의 AmazonTranslator는 주로 Amazon Translate를 사용하며,
        Bedrock은 저자원 언어 보정 시에만 필요하므로 지연 초기화가 효율적이다.
        worker/llm/bedrock.py의 invoke_text()는 미구현 상태이므로 직접 호출한다.
        """
        if self._bedrock_client is None:
            import boto3

            self._bedrock_client = boto3.client(
                "bedrock-runtime", region_name=self._region
            )
        return self._bedrock_client

    def _refine_with_claude(
        self, source_ko: str, draft_translation: str, target_lang: str
    ) -> str:
        """Claude를 사용하여 기계번역 초벌을 보정한다.

        Args:
            source_ko: 원본 한국어 텍스트
            draft_translation: Amazon Translate로 생성한 초벌 번역
            target_lang: 대상 언어 코드

        Returns:
            보정된 번역. 실패 시 draft_translation을 그대로 반환한다.
        """
        try:
            import json

            bedrock = self._get_bedrock_client()

            prompt = (
                f"Original Korean: {source_ko}\n"
                f"Machine translation ({target_lang}): {draft_translation}\n\n"
                "Please refine the translation for naturalness and accuracy. "
                "Keep the meaning identical. Return ONLY the refined translation, "
                "with no explanations, notes, or additional text."
            )

            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )

            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body,
            )

            result = json.loads(response["body"].read())
            refined = result["content"][0]["text"].strip()

            if refined:
                return refined
            return draft_translation

        except Exception as e:
            logger.warning(
                "Claude refinement failed for target_lang=%s: %s. Using draft translation.",
                target_lang,
                str(e),
            )
            return draft_translation


def get_translator() -> Translator:
    return AmazonTranslator(region=AWS_REGION) if PROVIDER_MODE == "aws" else MockTranslator()
