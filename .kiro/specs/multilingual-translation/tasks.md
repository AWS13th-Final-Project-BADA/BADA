# Implementation Plan: Multilingual Translation

## Overview

Implement the multilingual translation system for BADA's worker pipeline. This involves creating the `LanguageConfig` module, implementing `AmazonTranslator` with direct/pivot/pivot+refine strategies, enhancing `TranslationService.build_translation_pairs()` to include disclaimer and missing evidence translations, and adding long text chunking. The `TimelineService` already works with the Translator interface and needs minimal changes.

## Tasks

- [x] 1. Create LanguageConfig module and UnsupportedLanguageError
  - [x] 1.1 Create `worker/providers/language_config.py` with LanguageStrategy dataclass and SUPPORTED_LANGUAGES dict
    - Define `LanguageStrategy` dataclass with fields: `bada_code`, `translate_code`, `strategy`, `pivot_lang`, `needs_refinement`
    - Define `SUPPORTED_LANGUAGES` dict mapping eight language codes (ko, vi, en, id, km, ne, th, ja) to their strategies
    - Implement `get_language_strategy(lang_code: str) -> LanguageStrategy` that raises `UnsupportedLanguageError` for unknown codes
    - Define `UnsupportedLanguageError` exception class
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 1.2 Write property test for supported language validation (Property 8)
    - **Property 8: Supported Language Validation**
    - **Validates: Requirements 1.4, 7.3**
    - Use hypothesis to test that any string NOT in SUPPORTED_LANGUAGES raises UnsupportedLanguageError
    - Test that all six defined codes return valid LanguageStrategy objects

  - [ ]* 1.3 Write unit tests for LanguageConfig
    - Test each language code returns correct strategy ("none" for ko, "direct" for vi/en/id, "pivot+refine" for km/ne)
    - Test pivot_lang is "en" for km/ne and None for others
    - Test needs_refinement is True only for km/ne
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.6_

- [x] 2. Implement AmazonTranslator with translation strategies
  - [x] 2.1 Implement core `AmazonTranslator.translate()` method in `worker/providers/translate.py`
    - Import and use `get_language_strategy` from language_config
    - Handle no-op cases: empty text returns empty string, target "ko" returns source unchanged
    - Implement direct strategy: call `boto3 translate_text(Text, SourceLanguageCode="ko", TargetLanguageCode)`
    - Implement pivot strategy: ko→en→target (two Amazon Translate calls)
    - Implement pivot+refine strategy: ko→en→target + Claude refinement via existing `worker/llm/bedrock.py`
    - Wrap all API calls in try/except for graceful degradation (return source text on failure, log warning)
    - Validate target_lang against SUPPORTED_LANGUAGES, raise UnsupportedLanguageError if invalid
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4_

  - [x] 2.2 Implement `AmazonTranslator.translate_batch()` method
    - Add `translate_batch(texts: list[str], target_lang: str) -> list[str]` to Translator ABC and MockTranslator
    - Implement batch as iteration over translate() with per-item error isolation
    - Return source text for failed items, continue processing remaining
    - Short-circuit: if target is "ko", return input list unchanged
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.3 Implement long text chunking for texts exceeding 10KB
    - Add `_chunk_text(text: str, max_bytes: int = 10000) -> list[str]` helper
    - Split at sentence boundaries (Korean sentence-ending markers: 다., 요., 니다., etc.)
    - In translate(), detect oversized text and chunk→translate→concatenate
    - If a chunk fails, use source text for that chunk and continue
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 2.4 Implement Claude refinement helper for low-resource languages
    - Add `_refine_with_claude(source_ko: str, draft_translation: str, target_lang: str) -> str` private method
    - Use existing `worker/llm/bedrock.py` Bedrock client to invoke Claude
    - If Claude returns empty/error, fall back to unrefined draft
    - _Requirements: 3.4, 3.5_

  - [ ]* 2.5 Write property test for Korean identity (Property 2)
    - **Property 2: Identity for Korean**
    - **Validates: Requirements 1.2, 2.3, 6.2**
    - Use hypothesis: for any text, translate(text, "ko") == text
    - For any list, translate_batch(texts, "ko") == texts

  - [ ]* 2.6 Write property test for batch order and length preservation (Property 3)
    - **Property 3: Batch Order and Length Preservation**
    - **Validates: Requirements 2.1, 2.2**
    - Use hypothesis: for any list of texts, len(translate_batch(texts, lang)) == len(texts)

  - [ ]* 2.7 Write property test for empty text safety (Property 4)
    - **Property 4: Empty Text Safety**
    - **Validates: Requirements 1.3**
    - translate("", any_supported_lang) always returns ""

  - [ ]* 2.8 Write property test for graceful degradation (Property 5)
    - **Property 5: Graceful Degradation**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 2.4**
    - Mock Amazon Translate to always raise → translate() returns source text, no exception raised

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Enhance TranslationService with disclaimer and missing evidence pairs
  - [x] 4.1 Add disclaimer and missing evidence translation pairs to `worker/services/translation.py`
    - Add disclaimer (면책 고지) TranslationPair — always included regardless of other content
    - Add missing evidence translations when `result` contains `missing_evidences` list
    - Ensure every pair has non-empty source_text and translated_text (fallback to source on failure)
    - Attach `evidence_type` and `related_issue` metadata to every pair
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 8.1_

  - [ ]* 4.2 Write property test for disclaimer always included (Property 6)
    - **Property 6: Disclaimer Always Translated**
    - **Validates: Requirements 5.3**
    - Use hypothesis: for any result dict (with/without deductions, with/without suspected_unpaid), output always contains a disclaimer pair

  - [ ]* 4.3 Write property test for pair completeness (Property 7)
    - **Property 7: Pair Completeness**
    - **Validates: Requirements 5.4, 5.5, 5.6, 8.1**
    - For any generated pair: source_text is non-empty, translated_text is non-empty, evidence_type and related_issue are present

  - [ ]* 4.4 Write unit tests for build_translation_pairs
    - Test disclaimer is present when deduction_items is empty
    - Test deduction pairs are generated correctly
    - Test suspected_unpaid pair only when amount > 0
    - Test missing_evidences pairs are generated
    - Test graceful degradation: translator failure still produces valid pairs with source_text as fallback
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 5. Update TimelineService for consistency
  - [x] 5.1 Verify and update `worker/services/timeline.py` for translation consistency
    - Ensure `translate_batch` is used for efficiency when translating multiple descriptions
    - Verify description field is never modified (source preservation)
    - Ensure description_translated = description when target_lang is "ko"
    - Verify graceful degradation: if translate fails, description_translated = description
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.2, 8.4_

  - [ ]* 5.2 Write property test for source preservation (Property 1)
    - **Property 1: Source Preservation**
    - **Validates: Requirements 1.5, 6.3, 8.4**
    - Use hypothesis: for any text and language, original text object is never modified after translate()
    - For timeline events, description field remains unchanged after translation

  - [ ]* 5.3 Write unit tests for TimelineService translation
    - Test description_translated is populated for non-ko languages
    - Test description_translated == description when target_lang is "ko"
    - Test original description is preserved after translation
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Wire provider selection and update MockTranslator
  - [x] 6.1 Update `worker/providers/translate.py` with complete provider wiring
    - Add `translate_batch` to MockTranslator (identity function matching new ABC)
    - Update `get_translator()` to pass region from `config.AWS_REGION`
    - Ensure PROVIDER_MODE=local returns MockTranslator, PROVIDER_MODE=aws returns AmazonTranslator
    - Export `Translator`, `MockTranslator`, `AmazonTranslator`, `get_translator` from `__init__.py`
    - _Requirements: 1.2, 2.3, 4.4_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using hypothesis
- Unit tests validate specific examples and edge cases
- The existing `MockTranslator` (identity function) remains the default for local development
- `worker/llm/bedrock.py` already exists and provides the Bedrock client for Claude refinement
- No changes needed to `backend/app/models.py` — TranslationPair model already exists

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4"] },
    { "id": 3, "tasks": ["2.5", "2.6", "2.7", "2.8", "6.1"] },
    { "id": 4, "tasks": ["4.1", "5.1"] },
    { "id": 5, "tasks": ["4.2", "4.3", "4.4", "5.2", "5.3"] }
  ]
}
```
