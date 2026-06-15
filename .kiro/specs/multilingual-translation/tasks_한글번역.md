# 구현 계획 (한글 해설판)

## 개요

BADA 워커 파이프라인의 다국어 번역 시스템을 구현한다.
- `LanguageConfig` 모듈 생성 (언어별 전략 설정)
- `AmazonTranslator` 구현 (직접/피벗/보정 번역 전략)
- `TranslationService` 확장 (면책 고지 + 누락 자료 번역 추가)
- 초장문 텍스트 분할(chunking) 추가
- `TimelineService`는 이미 Translator 인터페이스로 동작하므로 최소한의 수정만

---

## 작업 목록

### ✅ 작업 1: LanguageConfig 모듈 생성

#### ✅ 1.1 `worker/providers/language_config.py` 파일 만들기
**뭘 만드나:**
- `LanguageStrategy` 데이터 클래스 — 각 언어의 번역 전략을 담는 구조체
  - `bada_code`: 내부 언어 코드 (ko, vi, en 등)
  - `translate_code`: Amazon Translate가 이해하는 코드
  - `strategy`: "none" / "direct" / "pivot+refine"
  - `pivot_lang`: 피벗할 때 거치는 중간 언어 (영어 또는 None)
  - `needs_refinement`: Claude 보정 필요 여부
- `SUPPORTED_LANGUAGES` 딕셔너리 — 8개 언어의 전략을 정의
- `get_language_strategy()` 함수 — 언어 코드 넣으면 전략 반환, 없는 코드면 에러
- `UnsupportedLanguageError` 에러 클래스

**관련 요구사항:** 7.1, 7.2, 7.3, 7.4, 7.5, 7.6

---

### ✅ 작업 2: AmazonTranslator 구현 (번역 핵심)

#### ✅ 2.1 `translate()` 메서드 구현
**뭘 만드나:**
- `worker/providers/translate.py`에 있던 `NotImplementedError` 스텁을 실제 코드로 교체
- 빈 텍스트 → 빈 문자열 반환 (API 안 부름)
- 대상이 한국어 → 원문 그대로 반환
- "direct" 전략(vi/en/id/th/ja): `boto3.translate_text()` 한 번 호출
- "pivot+refine" 전략(km/ne): 한국어→영어→대상어 (2번 호출) + Claude 보정
- 모든 API 호출을 try/except로 감싸서, 실패하면 원문 반환 + 경고 로그
- 지원 안 하는 언어면 `UnsupportedLanguageError` 발생

**관련 요구사항:** 1.1~1.5, 3.1~3.5, 4.1, 4.2, 4.4

#### ✅ 2.2 `translate_batch()` 메서드 구현
**뭘 만드나:**
- 텍스트 리스트를 받아서 각각 translate() 호출
- 하나가 실패해도 나머지는 계속 진행, 실패한 건 원문 반환
- 대상이 "ko"면 입력 그대로 반환 (API 안 부름)

**관련 요구사항:** 2.1~2.4

#### ✅ 2.3 초장문 텍스트 분할(chunking) 구현
**뭘 만드나:**
- `_chunk_text()` 헬퍼 함수 — 10KB 넘는 텍스트를 문장 경계로 자름
- 한국어 문장 끝 표현("습니다. ", "니다. ", "요. ", "다. ") 기준으로 분할
- translate()에서 텍스트가 10KB 넘으면 → 잘라서 → 각각 번역 → 합쳐서 반환
- 조각 하나 실패하면 그 조각만 원문 사용

**관련 요구사항:** 9.1, 9.2, 9.3

#### ✅ 2.4 Claude 보정 헬퍼 구현
**뭘 만드나:**
- `_refine_with_claude()` — 기계번역 초벌을 Claude에게 다듬어달라고 요청
- Bedrock Claude API 호출, 프롬프트: "원본 한국어 + 기계번역 초안 → 자연스럽게 고쳐줘"
- Claude가 실패하거나 빈 응답 → 초벌 번역 그대로 사용 (안 죽음)

**관련 요구사항:** 3.4, 3.5

---

### ✅ 작업 3: 체크포인트 — 여기까지 테스트 전부 통과 확인

---

### ✅ 작업 4: TranslationService 확장

#### ✅ 4.1 면책 고지 + 누락 자료 번역 쌍 추가
**뭘 만드나:**
- `worker/services/translation.py`의 `build_translation_pairs()` 함수 확장
- **면책 고지** 쌍 — 항상 포함 (다른 내용이 아무것도 없어도 무조건 들어감)
  - 원문: "본 자료는 법률자문이 아닌 상담 준비용 증거 정리 자료입니다..."
- **누락 자료 안내** 쌍 — result에 missing_evidences가 있으면 각각 번역 쌍 생성
- 모든 쌍에 evidence_type + related_issue 메타데이터 부착
- 번역 실패 시 → source_text를 translated_text에도 넣음 (빈 값 방지)

**관련 요구사항:** 5.1~5.6, 8.1

---

### ✅ 작업 5: TimelineService 업데이트

#### ✅ 5.1 타임라인 번역 일관성 확보
**뭘 만드나:**
- 개별 translate() 호출 대신 → `translate_batch()`로 한 번에 번역 (효율적)
- description 필드는 절대 수정 안 함 (원문 보존)
- 대상이 "ko"면 → description_translated = description
- 번역 실패 시 → description_translated에 원본 description을 넣음

**관련 요구사항:** 6.1~6.4, 8.2, 8.4

---

### ✅ 작업 6: Provider 연결 마무리

#### ✅ 6.1 provider 모드 전환 완성
**뭘 만드나:**
- `get_translator()`에서 `AWS_REGION`을 AmazonTranslator에 넘기도록 수정
- `PROVIDER_MODE=local` → MockTranslator (로컬 개발, AWS 없이)
- `PROVIDER_MODE=aws` → AmazonTranslator (실제 AWS 서비스 호출)
- `__init__.py`에서 주요 클래스 export

**관련 요구사항:** 1.2, 2.3, 4.4

---

### ✅ 작업 7: 최종 체크포인트 — 전체 테스트 통과 확인 (85개 통과!)

---

## 참고사항

- `*` 표시된 작업은 **선택사항** (property-based test). 더 견고하게 만들고 싶으면 나중에 추가
- 각 작업마다 관련 요구사항 번호가 매핑되어 있어서 "왜 이걸 하는지" 추적 가능
- `MockTranslator`(원문 그대로 반환)가 로컬 기본값 → AWS 없이도 전체 파이프라인이 돌아감
- DB 모델(TranslationPair)은 이미 있으므로 backend 코드는 안 건드림

---

## 작업 의존성 그래프 (순서)

```
Wave 0: [1.1] LanguageConfig 만들기
         ↓
Wave 1: [2.1] 핵심 translate() 구현
         ↓
Wave 2: [2.2] 배치 번역, [2.3] 텍스트 분할, [2.4] Claude 보정 — 병렬 가능
         ↓
Wave 3: [6.1] Provider 연결 — 선택적 property test도 이 시점
         ↓
Wave 4: [4.1] 대조표 확장, [5.1] 타임라인 업데이트 — 병렬 가능
         ↓
Wave 5: 선택적 테스트들 (property-based)
```

각 "Wave"는 앞 단계가 끝나야 시작할 수 있는 그룹이다.
같은 Wave 안의 작업들은 서로 독립적이라 동시에 진행해도 됨.

---

## 추가 작업 (테스트 중 발견된 개선사항 — 완료됨)

### ✅ 추가 작업 A: 프론트→API lang 파라미터 전달

- 분석 실행 시 현재 선택된 UI 언어를 `?lang=` 파라미터로 API에 전달
- 리포트 열기 시에도 `?lang=` 전달
- 파일: `backend/app/static/index.html`

### ✅ 추가 작업 B: 리포트 실시간 번역 (report.html 리팩터링)

- 기존: 분석 시점에 번역 저장 → 리포트에서 저장된 값만 표시 (언어 고정)
- 변경: 리포트 조회 시점에 DB의 한국어 원문을 `translator.translate()`로 실시간 번역
- 사용자가 언어를 바꿔도 분석을 다시 돌릴 필요 없음
- 파일: `backend/app/routers/analysis.py`

### ✅ 추가 작업 C: PDF 인쇄 버튼은 한국어 고정

- 리포트의 인쇄 버튼은 항상 `?lang=ko`로 한국어 리포트를 새 탭에 엶
- 공공기관/법무법인 제출용이므로 번역하지 않음
- `@media print` CSS로 인쇄 시 버튼 숨김

### ✅ 추가 작업 D: TRANSLATE_MODE 환경변수 분리

- `TRANSLATE_MODE=aws`로 번역만 실제 AWS 사용 가능 (LLM/OCR은 Mock 유지)
- `worker/config.py`에 `TRANSLATE_MODE` 추가
- `get_translator()`가 `TRANSLATE_MODE`를 참조하도록 수정

### ✅ 추가 작업 E: 대조표 증거유형 다국어 표시

- report.html에서 evidence_type 컬럼도 언어별 매핑 (en/vi/th/ja)
- 한국어 모드에서는 한국어 그대로 표시

### ✅ 추가 작업 F: 태국어(th) + 일본어(ja) 언어 추가

- `language_config.py`에 th, ja를 "direct" 전략으로 추가 (8개 언어)
- `backend/app/schemas.py`의 Lang Literal에 "th", "ja" 추가
- `backend/app/routers/analysis.py`의 report.html UI 텍스트에 th/ja 추가
- `frontend/locales/th.json`, `ja.json` 생성
- Amazon Translate가 ko→th, ko→ja 직접 지원하므로 피벗 불필요

### ✅ 추가 작업 G: 프론트엔드 UI 전면 i18n 적용 (develop 브랜치)

- `js/upload.js` ROWS 배열: 한국어 하드코딩 → i18n 키 참조 (5개 카드 + 촬영·파일)
- `js/case.js` ISSUES 객체: 문제유형 칩 5개 다국어
- `js/analysis.js` renderResult(): 결과 페이지 상태 메시지, 검증 포인트, GPS, 타임라인 다국어
- `js/core.js` applyLang(): placeholder 갱신, 업로드 카드 재렌더, 문제유형 칩 재렌더, 결과 페이지 언어 변경 시 조용한 재분석 + 토스트
- `index.html`: input placeholder → data-ph 속성, 섹션 제목 → data-k 속성
- `js/i18n.js`: 8개 언어 전부에 40+ 신규 키 추가 (id/km/ne/th/ja 포함)
- 리포트(report.html) 다국어 UI dict 재적용 (ko/en/vi/ja/th, 나머지 영어 fallback)
