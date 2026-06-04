# Requirements Document

## Introduction

BADA 다국어 번역 기능은 외국인 노동자가 분석 결과(타임라인, 공제 내역, 미지급 의심 금액, 면책 고지)를 자신의 모국어로 이해할 수 있도록 동적 콘텐츠를 번역하는 시스템이다. Amazon Translate를 기본 엔진으로 사용하며, 저자원 언어(크메르어·네팔어)에는 영어 피벗 및 Claude 보정을 적용한다. 원문은 항상 병기하여 번역 오류 시 확인이 가능하도록 한다.

## Glossary

- **Translator**: Amazon Translate API를 캡슐화하여 텍스트 번역을 수행하는 컴포넌트
- **TranslationService**: 분석 결과에서 번역 대상을 추출하고 원문-번역 대조표(TranslationPair)를 생성하는 서비스 레이어
- **TimelineService**: 타임라인 이벤트 설명을 모국어로 번역하여 description_translated 필드에 저장하는 서비스
- **LanguageConfig**: 지원 언어 목록, 코드 매핑, 번역 전략을 중앙 관리하는 설정 모듈
- **TranslationPair**: 원문(source_text)과 번역문(translated_text)을 함께 보관하는 데이터 구조
- **LanguageStrategy**: 각 언어에 대한 번역 전략(direct/pivot/pivot+refine)을 정의하는 데이터 클래스
- **Pivot_Translation**: 소스→영어→타겟 2단계 번역 경로
- **Graceful_Degradation**: API 오류 시 원문을 반환하여 시스템 중단을 방지하는 전략
- **SUPPORTED_LANGUAGES**: 시스템이 지원하는 언어 코드 집합 (ko, vi, en, id, km, ne)

## Requirements

### Requirement 1: 단일 텍스트 번역

**User Story:** As a 외국인 노동자, I want 한국어 분석 결과를 모국어로 번역받고 싶다, so that 법률 상담 전에 내 사건 내용을 이해할 수 있다.

#### Acceptance Criteria

1. WHEN a non-empty Korean text and a supported target language are provided, THE Translator SHALL return a translated string in the target language
2. WHEN the target language is "ko", THE Translator SHALL return the source text unchanged (identity function)
3. WHEN an empty string is provided as source text, THE Translator SHALL return an empty string without making any API call
4. WHEN the target language is not in SUPPORTED_LANGUAGES, THE Translator SHALL raise an UnsupportedLanguageError with a descriptive message
5. THE Translator SHALL never modify the original source text object passed as input

### Requirement 2: 배치 번역

**User Story:** As a 시스템 운영자, I want 여러 텍스트를 한번에 번역하고 싶다, so that 네트워크 라운드트립을 최소화하고 파이프라인 성능을 확보할 수 있다.

#### Acceptance Criteria

1. WHEN a list of texts and a target language are provided, THE Translator SHALL return a list of translated strings with the same length as the input
2. WHEN batch translation is performed, THE Translator SHALL preserve the order so that the i-th output corresponds to the i-th input
3. WHEN the target language is "ko", THE Translator SHALL return the input list unchanged without making any API call
4. IF any individual text in the batch fails to translate, THEN THE Translator SHALL return the source text for that item and continue translating the remaining items

### Requirement 3: 언어별 번역 전략 적용

**User Story:** As a 시스템 설계자, I want 각 언어에 맞는 최적 번역 전략이 자동 적용되길 원한다, so that 저자원 언어도 최대한 높은 번역 품질을 확보할 수 있다.

#### Acceptance Criteria

1. WHEN the target language is "vi", "en", or "id", THE Translator SHALL use the direct strategy (ko→target via Amazon Translate)
2. WHEN the target language is "km" or "ne", THE Translator SHALL use the pivot+refine strategy (ko→en→target + Claude refinement)
3. WHEN pivot translation is used, THE Translator SHALL first translate Korean to English, then English to the target language
4. WHEN Claude refinement is applied, THE Translator SHALL send the original Korean text and the machine-translated draft to Bedrock Claude for naturalness improvement
5. IF Claude refinement fails or returns empty output, THEN THE Translator SHALL fall back to the unrefined machine translation draft

### Requirement 4: 그레이스풀 디그레이데이션

**User Story:** As a 외국인 노동자, I want 번역 API가 실패해도 결과를 볼 수 있길 원한다, so that 시스템 장애 시에도 원문으로라도 사건 내용을 확인할 수 있다.

#### Acceptance Criteria

1. IF the Amazon Translate API fails with any error, THEN THE Translator SHALL return the source text unchanged and log a warning
2. IF a translation timeout occurs, THEN THE Translator SHALL return the source text unchanged without raising an exception to the caller
3. WHEN graceful degradation occurs, THE TranslationPair SHALL store the source text in both source_text and translated_text fields
4. THE Translator SHALL never raise an unhandled exception to the calling pipeline for translation failures

### Requirement 5: 원문-번역 대조표 생성

**User Story:** As a 외국인 노동자, I want 공제 내역과 미지급 의심 금액을 원문과 함께 모국어로 확인하고 싶다, so that 상담기관 방문 시 정확한 내용을 전달할 수 있다.

#### Acceptance Criteria

1. WHEN analysis results contain deduction items, THE TranslationService SHALL create a TranslationPair for each deduction item with source_text and translated_text
2. WHEN analysis results contain a suspected unpaid amount greater than zero, THE TranslationService SHALL create a TranslationPair for the suspected unpaid description
3. THE TranslationService SHALL always include a disclaimer (면책 고지) TranslationPair in the output regardless of other analysis content
4. WHEN a TranslationPair is created, THE TranslationService SHALL ensure source_text is never empty
5. WHEN a TranslationPair is created, THE TranslationService SHALL ensure translated_text is never empty (using source_text as fallback on failure)
6. WHEN building translation pairs, THE TranslationService SHALL attach evidence_type and related_issue metadata to each pair

### Requirement 6: 타임라인 이벤트 번역

**User Story:** As a 외국인 노동자, I want 사건 타임라인의 각 이벤트 설명을 모국어로 읽고 싶다, so that 사건 경과를 시간 순서대로 이해할 수 있다.

#### Acceptance Criteria

1. WHEN a timeline event has a description, THE TimelineService SHALL translate the description into the target language and store it in description_translated
2. WHEN the target language is "ko", THE TimelineService SHALL set description_translated equal to description
3. WHEN timeline translation is performed, THE TimelineService SHALL preserve the original Korean description in the description field unchanged
4. IF translation of a timeline event description fails, THEN THE TimelineService SHALL set description_translated to the original Korean description

### Requirement 7: 지원 언어 관리

**User Story:** As a 시스템 관리자, I want 지원 언어와 번역 전략을 중앙에서 관리하고 싶다, so that 새 언어 추가 시 일관된 방식으로 확장할 수 있다.

#### Acceptance Criteria

1. THE LanguageConfig SHALL define exactly six supported languages: ko, vi, en, id, km, ne
2. WHEN a language code is queried, THE LanguageConfig SHALL return the corresponding LanguageStrategy with bada_code, translate_code, strategy, pivot_lang, and needs_refinement fields
3. WHEN a language code not in SUPPORTED_LANGUAGES is queried, THE LanguageConfig SHALL raise an UnsupportedLanguageError
4. THE LanguageConfig SHALL assign "direct" strategy to vi, en, and id
5. THE LanguageConfig SHALL assign "pivot+refine" strategy to km and ne with pivot_lang set to "en"
6. THE LanguageConfig SHALL assign "none" strategy to ko (no translation needed)

### Requirement 8: 원문 병기 원칙

**User Story:** As a 외국인 노동자, I want 번역 결과 옆에 항상 한국어 원문이 함께 표시되길 원한다, so that 번역이 부정확할 때 상담기관에서 원문을 참조할 수 있다.

#### Acceptance Criteria

1. THE TranslationPair SHALL always contain both source_text (Korean original) and translated_text (target language)
2. THE TimelineService SHALL always provide both description (Korean) and description_translated (target language) for every translated event
3. WHEN displaying translated content, THE System SHALL present the source text alongside the translated text (side-by-side)
4. THE System SHALL never discard or overwrite the original Korean source text during any translation operation

### Requirement 9: 초장문 텍스트 처리

**User Story:** As a 시스템 운영자, I want Amazon Translate API 제한을 초과하는 긴 텍스트도 정상 번역되길 원한다, so that 어떤 길이의 분석 결과도 누락 없이 번역할 수 있다.

#### Acceptance Criteria

1. WHEN source text exceeds 10,000 bytes (Amazon Translate limit), THE Translator SHALL split the text at sentence boundaries
2. WHEN text is chunked, THE Translator SHALL translate each chunk individually and concatenate the results in order
3. IF a chunk fails to translate, THEN THE Translator SHALL use the source text for that chunk and continue with remaining chunks
