# BADA 다국어 번역 — 내부 동작 원리

> 한 문장 원칙: **분석 결과는 한국어로 저장하고, 조회 시점에 실시간 번역한다.**
> 번역 실패 시 원문 반환(graceful degradation). 원문은 항상 병기(side-by-side).

---

## 0. 큰 그림

```
[사용자] 리포트 조회 (?lang=vi)
   │
   ▼
[backend/routers/analysis] → DB에서 한국어 원문 로드
   │
   ▼
[worker/providers/translate] → 언어별 전략 분기
   │
   ├─ vi/en/id/th/ja → Amazon Translate (ko→target 직접)
   ├─ km/ne          → Amazon Translate (ko→en→target 피벗) + Claude 보정
   └─ ko             → 번역 없음 (원문 그대로)
   │
   ▼
결과 JSON (source_text + translated_text 쌍) → 프론트 표시
```

핵심: **분석을 다시 돌리지 않아도** 언어를 바꿔가며 리포트를 볼 수 있다.

### 구현 경로 (2026-07-02 완성)
- **Worker**: `pipeline.py` → 분석 결과 항상 한국어로 생성 → DB에 한국어 저장
- **Backend**: `GET /analysis?lang=en` → `backend/app/services/translation.py` → Amazon Translate 실시간 번역
- **FE**: `/analysis?lang=${locale}` 호출 → 사용자 언어로 화면 표시
- **PDF**: `lang="ko"` 고정 → 항상 한국어 (노동부/법원 제출용 원본)

---

## 1. 지원 언어 (8개)

| 코드 | 언어 | 전략 | 비고 |
|------|------|------|------|
| ko | 한국어 | none | 번역 안 함 |
| vi | 베트남어 | direct | 데모 완성도 1순위 |
| en | 영어 | direct | 데모 완성도 1순위 |
| id | 인도네시아어 | direct | |
| th | 태국어 | direct | |
| ja | 일본어 | direct | |
| km | 크메르어 | pivot+refine | ko→en→km + Claude 보정 |
| ne | 네팔어 | pivot+refine | ko→en→ne + Claude 보정 |

설정: `worker/providers/language_config.py`의 `SUPPORTED_LANGUAGES` 딕셔너리.

---

## 2. 파일 구조

```
worker/
├─ providers/
│  ├─ language_config.py   # LanguageStrategy, SUPPORTED_LANGUAGES, get_language_strategy()
│  └─ translate.py         # Translator ABC, MockTranslator, AmazonTranslator, get_translator()
├─ services/
│  ├─ translation.py       # build_translation_pairs() — 원문-번역 대조표 생성
│  └─ timeline.py          # build_timeline() — 타임라인 이벤트 번역
└─ config.py               # TRANSLATE_MODE 환경변수
```

---

## 3. 번역 전략 상세

### Direct (vi/en/id/th/ja)
```
한국어 텍스트 → Amazon Translate (ko→vi) → 번역 결과
```

### Pivot + Refine (km/ne)
```
한국어 텍스트
  → Amazon Translate (ko→en)     ← 1단계: 영어 피벗
  → Amazon Translate (en→km)     ← 2단계: 영어→대상어
  → Bedrock Claude (보정 요청)    ← 3단계: 자연스럽게 다듬기
  → 최종 번역
```
- Claude 보정 실패 시 → 2단계 결과(기계번역 초안) 그대로 사용

### 초장문 처리 (10KB 초과)
- Amazon Translate API 제한 = 10,000바이트
- 문장 경계("습니다. ", "니다. ", "요. ", "다. ")에서 분할
- 각 조각 번역 후 순서대로 결합
- 조각 하나 실패 → 그 조각만 원문 사용

---

## 4. 번역 대상 (build_translation_pairs)

| 항목 | 조건 |
|------|------|
| 공제 항목 설명 | result에 deduction_items가 있으면 |
| 미지급 의심 금액 설명 | suspected_unpaid > 0이면 |
| 누락 증거 안내 | missing_evidences가 있으면 |
| **면책 고지** | **항상 포함** (다른 내용이 없어도) |

모든 항목은 `{source_text, translated_text, evidence_type, related_issue}` 구조.

---

## 5. 타임라인 번역 (build_timeline)

- 각 이벤트의 `description`(한국어)을 `translate_batch()`로 일괄 번역
- 결과를 `description_translated`에 저장
- target이 "ko"면 → description_translated = description (복사)
- 번역 실패 → description_translated에 원본 한국어 넣음
- **원본 description은 절대 수정 안 함**

---

## 6. 리포트 실시간 번역

- `GET /cases/{id}/report.html?lang=vi`
- DB에 저장된 한국어 원문을 **조회 시점에** Amazon Translate로 번역
- UI 라벨·섹션 제목·면책 고지도 lang에 따라 전환 (미리 정의된 dict)
- `?lang=ko` → 번역 없이 원문 표시, API 호출 안 함

---

## 7. PDF 인쇄

- 인쇄 버튼은 **항상 `?lang=ko`** 리포트를 새 탭에 엶
- 이유: 공공기관(고용노동부)·법무법인 제출용 → 한국어 고정
- `@media print` CSS로 인쇄 시 버튼 숨김

---

## 8. 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `PROVIDER_MODE` | local | local=MockTranslator, aws=AmazonTranslator |
| `TRANSLATE_MODE` | (PROVIDER_MODE 따름) | 번역만 독립 전환. `aws`로 설정 시 나머지 Mock이어도 번역만 실제 AWS |
| `AWS_REGION` | ap-northeast-2 | Amazon Translate 리전 |

---

## 9. Graceful Degradation (실패 처리)

- Amazon Translate API 실패 → 원문 그대로 반환 + 경고 로그
- Claude 보정 실패 → 기계번역 초안 사용
- 배치 중 일부 실패 → 실패 항목만 원문, 나머지 정상 번역
- **번역 실패로 예외가 파이프라인까지 전파되면 안 됨**

---

## 10. 테스트

```bash
cd worker && python -m pytest tests/test_translate.py tests/test_translation_service.py -v
```

- 번역 관련 테스트 ~30개 (Worker 전체 ~168개 + property-based 13개)
- MockTranslator(원문 그대로 반환)로 전체 파이프라인이 로컬에서 동작
- 실제 번역 품질은 `PROVIDER_MODE=aws`로 수동 확인

---

## 11. 프론트엔드 i18n (정적 UI)

- `backend/app/static/js/i18n.js` — 8개 언어 × 40+ 키
- `index.html`에서 `data-k` 속성으로 일괄 치환 (`applyLang()`)
- 언어 변경 시 결과 페이지 자동 재분석 (해당 lang으로)
- 정적 UI ≠ 동적 번역: UI 라벨은 JSON, 분석 결과는 Amazon Translate
