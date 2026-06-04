---
inclusion: always
---

# BADA — 도메인 모델 (Domain Steering)

> 데이터 모델·엔티티·규칙 로직을 생성할 때 이 정의를 따른다.
> 컬럼명·enum 값은 여기 정의된 것을 그대로 사용한다.

## 1. 핵심 엔티티 (DB 스키마 요약)

### cases
- `workplace_name`, `employer_name`, `work_start_date`, `work_end_date(NULL=진행중)`
- `agreed_hourly_wage(INTEGER, 원)`, `agreed_weekly_hours(DECIMAL)`
- `issue_types(JSONB)`: `["wage_unpaid","statement_mismatch","deduction","overtime","no_contract"]`
- `status`: `draft / analyzing / completed`

### evidences
- `file_type`: `image / pdf / text`
- `category`: `contract / schedule / payment / chat / statement / other`
- `ocr_status`: `pending / processing / done / failed`
- `ocr_text(TEXT)`, `extracted_entities(JSONB)`

### timeline_events
- `event_date(DATE, NULL 가능)`, `event_type`: `work_start / wage_promise / payment / underpayment / chat / gps`
- `description(한국어)`, `description_translated(모국어)`
- `source_evidence_id(FK)`, `confidence`: `high / medium / low`

### translation_pairs (원문-번역 대조표)
- `source_text`, `translated_text`, `evidence_type`, `related_issue`, `source_evidence_id`

### analysis_results
- `total_expected_wage`, `total_received_wage`, `suspected_unpaid`
- `deduction_items(JSONB)`: `[{"name":"기숙사비","amount":250000,"check":"계약서 명시 확인 필요"}]`
- `calculation_detail(JSONB)`, `timeline_summary`, `missing_evidences(JSONB)`
- `pdf_ko_s3_key`, `pdf_native_s3_key`

### gps_logs (GPS-lite)
- `case_id(FK)`, `ts(TIMESTAMP)`, `lat(DECIMAL)`, `lng(DECIMAL)`
- `status`: `IN_WORKPLACE / OUTSIDE`
- `is_mocked(BOOLEAN)` — true면 교차검증에서 배제
- `source`: `web_geo / seed / app`

### workplaces (지오펜스)
- `case_id(FK)`, `polygon(GEOGRAPHY/GEOMETRY)` 또는 `center_lat/center_lng + radius_m(기본 50)`

## 2. 엔티티 추출 대상 (LLM이 뽑을 것)

날짜 · 금액 · 시급/월급 · 공제항목 · 사업장명 · 사업주명 · 지급일 · 근무시간 · 장소명.
발화 분류(카톡/문자): `지급약속` / `근무지시` / `미지급인정` / `회피성답변`(MVP는 지급약속·임의공제통보 중심).

## 3. 규칙 기반 계산 (생성형 금지 — architecture.md 참조)

### 급여-입금 차액
```
기대급여 = agreed_hourly_wage × 확인된 근무시간 합
실수령   = 입금내역(payment) 합
미지급_의심 = 기대급여 − 실수령  (단, "의심"으로만 표기; "확정" 금지)
```
- 근무시간이 불확실하면 계산하지 말고 "출퇴근 기록 있으면 더 정확" 누락 안내.

### 공제 분류 사전 (정규화 — 변형 표기 흡수)
- 기숙사비: `기숙사비, 숙소비, 기숙비, 방값, dormitory`
- 식비: `식비, 밥값, meal`
- 작업복/장비: `작업복비, 장비비, 유니폼, 안전화`
- 기타: 위에 안 맞으면 `기타공제` + "확인 필요"
- 각 공제는 **"계약서 명시 확인 필요"** 플래그를 기본 부착.

### 누락 증거 체크리스트 (규칙)
- 입금내역 없음 → "통장 입금내역 필요"
- 근무시간 근거 없음 → "출퇴근 기록/근무표 필요"
- 사업장 식별정보 부족 → "계약서 첫 페이지 필요"
- 지급약속 근거 없음 → "사업주 대화(카톡) 필요"

## 4. GPS-lite 규칙 (Phase 3 풀버전 아님 — MVP 범위 엄수)

- **지오펜스 판정**: PostGIS `ST_Contains`(폴리곤) 또는 `ST_Distance ≤ radius_m`. 각 ping에 `IN_WORKPLACE/OUTSIDE` 태깅.
- **Fake GPS**: 탐지 고도화는 하지 않는다. 클라이언트가 보낸 `is_mocked` 플래그만 받아 저장하고, true면 교차검증·타임라인에서 **자동 배제**.
- **교차검증 규칙**: 같은 시간대(±N분)에 카톡 도착성 발화("도착했습니다" 등)와 `IN_WORKPLACE` ping이 함께 있으면 해당 이벤트에 "정황 일치" 표시. (생성형 아님 — 시간 매칭 규칙)
- **PDF 반영**: 일(Day) 단위로 요약한 GPS 타임라인을 Evidence Pack에 섹션으로 병합.
- **데이터 소스**: 분석은 항상 `seed` 로그로도 돌아가야 한다(데모 안전망). `web_geo`는 발표용 라이브 핑.
- ⚠️ 백그라운드 추적·PostGIS 고성능·위치정보법 자동파기 스케줄러는 **MVP 범위 밖**(네이티브 앱은 스트레치).

## 5. 다국어

- 지원: ko + vi, km, ne, id, en. **데모 완성도는 vi + en 우선.**
- 제출용 PDF = 한국어 고정. 이해용 = 모국어. 원문은 항상 병기.
