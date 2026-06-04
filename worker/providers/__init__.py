"""Provider seam — 각 기능 담당자가 'aws' 구현만 채우면 되는 교체 지점.

- llm.py       : 문장화·요약 (타임라인/요약 담당)
- ocr.py       : 이미지/문서 → 텍스트·엔티티 (OCR 담당)
- translate.py : 번역 (다국어 담당)

PROVIDER_MODE=local 이면 Mock(결정적, AWS 불필요)으로 전체 파이프라인이 돈다.
PROVIDER_MODE=aws 이면 각 *Aws* 구현이 선택된다(현재 NotImplemented 스텁).
설계 원칙: 이 계층은 텍스트 입출력만. 계산·판정은 worker/rules (architecture.md).
"""

from .language_config import (
    LanguageStrategy,
    SUPPORTED_LANGUAGES,
    UnsupportedLanguageError,
    get_language_strategy,
)
from .translate import (
    AmazonTranslator,
    MockTranslator,
    Translator,
    get_translator,
)

__all__ = [
    "AmazonTranslator",
    "LanguageStrategy",
    "MockTranslator",
    "SUPPORTED_LANGUAGES",
    "Translator",
    "UnsupportedLanguageError",
    "get_language_strategy",
    "get_translator",
]
