"""Language configuration — 지원 언어 목록, 코드 매핑, 번역 전략 중앙 관리.

SUPPORTED_LANGUAGES 딕셔너리로 각 언어의 번역 전략을 조회한다.
- ko: none (번역 불필요)
- vi, en, id, th, ja: direct (Amazon Translate 단독)
- km, ne: pivot+refine (ko→en→target + Claude 보정)
"""
from __future__ import annotations

from dataclasses import dataclass


class UnsupportedLanguageError(Exception):
    """지원하지 않는 언어 코드가 요청되었을 때 발생."""

    def __init__(self, lang_code: str) -> None:
        self.lang_code = lang_code
        super().__init__(
            f"Unsupported language code: '{lang_code}'. "
            f"Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}"
        )


@dataclass(frozen=True)
class LanguageStrategy:
    """각 언어에 대한 번역 전략을 정의하는 데이터 클래스.

    Attributes:
        bada_code: BADA 내부 언어 코드 (ko, vi, en, id, km, ne)
        translate_code: Amazon Translate API에서 사용하는 언어 코드
        strategy: 번역 전략 ("none" | "direct" | "pivot+refine")
        pivot_lang: 피벗 언어 코드 (피벗 필요 시 "en", 아니면 None)
        needs_refinement: Claude 보정 적용 여부 (저자원 언어만 True)
    """

    bada_code: str
    translate_code: str
    strategy: str
    pivot_lang: str | None
    needs_refinement: bool


SUPPORTED_LANGUAGES: dict[str, LanguageStrategy] = {
    "ko": LanguageStrategy(
        bada_code="ko",
        translate_code="ko",
        strategy="none",
        pivot_lang=None,
        needs_refinement=False,
    ),
    "vi": LanguageStrategy(
        bada_code="vi",
        translate_code="vi",
        strategy="direct",
        pivot_lang=None,
        needs_refinement=False,
    ),
    "en": LanguageStrategy(
        bada_code="en",
        translate_code="en",
        strategy="direct",
        pivot_lang=None,
        needs_refinement=False,
    ),
    "id": LanguageStrategy(
        bada_code="id",
        translate_code="id",
        strategy="direct",
        pivot_lang=None,
        needs_refinement=False,
    ),
    "km": LanguageStrategy(
        bada_code="km",
        translate_code="km",
        strategy="pivot+refine",
        pivot_lang="en",
        needs_refinement=True,
    ),
    "ne": LanguageStrategy(
        bada_code="ne",
        translate_code="ne",
        strategy="pivot+refine",
        pivot_lang="en",
        needs_refinement=True,
    ),
    "th": LanguageStrategy(
        bada_code="th",
        translate_code="th",
        strategy="direct",
        pivot_lang=None,
        needs_refinement=False,
    ),
    "ja": LanguageStrategy(
        bada_code="ja",
        translate_code="ja",
        strategy="direct",
        pivot_lang=None,
        needs_refinement=False,
    ),
}


def get_language_strategy(lang_code: str) -> LanguageStrategy:
    """언어 코드에 해당하는 LanguageStrategy를 반환한다.

    Args:
        lang_code: BADA 내부 언어 코드 (예: "ko", "vi", "km")

    Returns:
        해당 언어의 LanguageStrategy 객체

    Raises:
        UnsupportedLanguageError: lang_code가 SUPPORTED_LANGUAGES에 없는 경우
    """
    if lang_code not in SUPPORTED_LANGUAGES:
        raise UnsupportedLanguageError(lang_code)
    return SUPPORTED_LANGUAGES[lang_code]
