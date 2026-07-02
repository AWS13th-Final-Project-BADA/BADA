## 증거 수집 에이전트 — 구현 현황 총정리

---

### 목적

사용자가 파일을 일일이 찾아 올리는 대신, 디바이스 갤러리에서 증거를 **자동 탐색·분류·추천**한다. AI는 추천만, 최종 등록은 사용자 승인(HITL).

---

### 4단계 파이프라인

| 단계 | 위치 | 동작 | 비용 |
|---|---|---|---|
| 1 메타데이터 필터 | 디바이스 | **근무 시작일 −30일 ~ 현재** + 스크린샷/카톡/다운로드/카메라 + 이미지 | 0원 |
| 2 온디바이스 OCR + 키워드 | 디바이스 | ML Kit/Vision 텍스트 추출 → "급여/임금/계약/입금/체불" 키워드 매칭 | 0원 |
| 3 경량 모델 분류 | 디바이스 | TFLite/CoreML (현재는 파일명·폴더 키워드 스코어 폴백) | 0원 |
| 4 서버 분류·OCR·저장 | 서버 | Bedrock/Upstage로 정밀 추출 + DB 저장 | ~30원/건 |

> **기간 필터 주의**: 종료일(endDate)은 항상 **현재 시점**으로 고정한다.
> 퇴직 후 캡처한 카톡·명세서 사진도 수집 대상이어야 하므로 `work_end_date`로 자르지 않는다.

**네이티브 앱 흐름 (현행)**: 스캔(1~3단계) 완료 → 후보를 바로 업로드(`category=auto`) →
`/extract` fire-and-forget 호출로 서버 OCR 트리거 → 분석 화면으로 이동. 사용자는 분석 결과를 **사후 검증**한다(HITL).
(원래 설계의 "3단계 후 recommend/maybe 표시 → 사용자 선택 → 4단계 진입" 카드형 승인 UI는 mobile/src 원본에만 있고, 네이티브 앱은 자동 진행 방식으로 단순화됨.)

---

### 서버 엔드포인트

| 엔드포인트 | 역할 |
|---|---|
| `POST /cases/{id}/evidences/scan` | 여러 이미지 분류만(OCR X) → 등급별 후보 |
| `POST /cases/{id}/evidences/assess` | 1장 분류 + OCR + 키워드 교차검증 |
| `POST /cases/{id}/evidences/agent-upload` | 승인된 파일 일괄 등록(category=auto) |
| `POST /cases/{id}/evidences/upload` | 개별 파일 업로드 (카테고리 지정) |
| `POST /cases/{id}/evidences/extract` | 자동분류 + OCR 1회 + 저장 |
| `GET /cases/{id}/evidences/extract` | OCR 진행 상태 폴링 |
| `PATCH /cases/{id}/evidences/{eid}/entities` | 사용자 수정 저장 |
| `POST /cases/{id}/evidences/{eid}/restore` | 제외된 파일 되살리기 |

---

### 정확성 강화 3종 (서버 측)

1. **교차검증** — classify(형태 분류) + OCR(실제 글자) 대조
2. **키워드 사전 검증** — 형태 분류와 내용 키워드 일치 여부 (규칙, 비용 0)
3. **신뢰도 임계값 분기** — auto_accept / needs_review / rejected

---

### 프론트 UI (mobile-native)

- **에이전트 스캔 카드** (보라색) — `app/cases/upload.tsx`의 "AI 증거 탐색" 카드 탭 → `scanGallery()` 실행
- **자동 진행** — 스캔 후보를 바로 업로드(`category=auto`) → `/extract` 트리거 → 분석 화면 이동 (별도 승인 카드 없음)
- **파일 리스트** — 최대 5개 표시 + "N개 더 보기/접기" 토글 (수백 장 스크롤 방지), 이미지 썸네일 미리보기
- **제외 되살리기** — 서버가 무관 판정한 파일은 "되살리기" 버튼 → `/restore` → 재추출
- **HITL 사후 검증** — 분석 결과 화면에서 OCR 추출값을 확인·수정(`PATCH /entities`)

---

### 업로드 방식 3가지

| 방식 | 설명 |
|---|---|
| 에이전트 스캔 | 여러 장 선택 → AI가 증거 선별·추천 → 사용자 승인 |
| 여러 장 한 번에 | category=auto, 서버가 자동 분류 (에이전트 추천 없이 전부 등록) |
| 개별 카테고리 | 계약서·명세서·입금내역·카톡·기타·오디오 각각 선택 업로드 |

---

### OCR 추출 결과 UI

- 파일별 카드: 상태 배지(읽는중/읽음/실패), 자동분류 근거(confidence + reason)
- 편집 가능한 필드: 시급·월급·근무일수·지급일·연장시간·공제항목·금액항목
- confidence low 항목에 ⚠️ 배지
- "수정 저장" 버튼 → PATCH → sanity·quality 재계산 반영
- evidence_quality: 증거력 점수 + 체크리스트 + 경고 표시
- sanity check: 값 이상치 감지 → 노랑 카드 표시

---

### 디바이스 코드

| 파일 | 역할 |
|---|---|
| `mobile-native/src/features/evidence/agent.ts` | 스캔(1~3단계) + `uploadApprovedCandidates`(업로드 + `/extract` 트리거) |
| `mobile-native/app/cases/upload.tsx` | 에이전트 스캔 UI + 업로드/분석 진입 |
| `mobile/src/evidence-agent.ts` | 원본 Capacitor 버전 (4단계 풀 파이프라인 + 카드형 승인, 참고용) |
| `mobile/src/evidence-agent.scenario.ts` | Node.js 시나리오 데모 (AWS 불필요) |

네이티브 앱(`mobile-native`)은 Expo 기반이라 ML Kit OCR이 없어 2단계는 **파일명·폴더 키워드 스코어**로 대체한다.
`mobile/src`의 `ocrFn`/`classifyFn` 콜백 기반 풀 파이프라인은 Capacitor 네이티브 브릿지 연결 시 사용.

---

### 워커 코드

| 파일 | 역할 |
|---|---|
| `worker/rules/category_keywords.py` | 키워드 사전 + 교차검증 규칙 |
| `worker/services/evidence_intake.py` | 서버 분류 (스캔/정밀/배치) |
| `backend/app/services/intake_service.py` | worker 호출 브릿지 |

---

### 비용/속도 (3000장 기준)

- 1~3단계(디바이스): 0원, 20~40초
- 4단계(서버): 깔때기 거친 후 ~280원 (안 거치면 ~7,500원 → **27배 절감**)

---

### GPS 기능 (에이전트와 연동)

재직 중 실시간 위치 증거를 수집하고, 카톡 발화와 교차검증하여 Evidence Pack에 병합한다.

**모바일 (`mobile-native/app/gps.tsx`, `src/features/gps/api.ts`)**
- 사건 생성 시 근무지 등록 (주소 검색/현재위치/좌표 직접입력, 반경 50~500m) → `POST /gps/workplace`
- 홈 GPS 스위치 → `expo-location` foreground watch로 핑 수집 → `POST /gps/ping`
- `is_mocked` 플래그(OS 제공)를 그대로 전송 (조작 GPS 탐지 고도화는 안 함, 플래그만 신뢰)
- 로그 조회(`/gps/logs`) + 일별 요약(`/gps/summary`)

**백엔드 (`backend/app/routers/gps.py`)**
- `POST /gps/workplace` — 지오펜스 중심·반경 등록
- `POST /gps/ping` — 핑 수신 → `_haversine_m`로 IN/OUTSIDE 판정 + **chain_hash 체인 무결성**(직전 핑 해시 연결)
- `GET /gps/logs` — 핑 목록
- `GET /gps/verify` — 해시 체인 위변조 검증
- `GET /gps/summary` — 일별 요약 + SHA-256 무결성 해시

**규칙 엔진 (`worker/rules/geofence.py`) — 순수 함수, LLM 금지**
- `tag_ping` / `tag_logs` — haversine 거리로 근무지 반경 안/밖 태깅
- 배제 규칙: `is_mocked=True`(조작핑) + `is_delayed_upload=True`(지연 업로드) → 교차검증·타임라인에서 자동 배제(기록은 보존)
- `cross_check` — 카톡 "도착" 발화 ±30분 내 IN_WORKPLACE 핑 존재 시 "정황 일치"(match=True), 없으면 match=False로 불일치도 추적
- `summarize_by_day` — 일 단위 체류시간 추정(핑 간 실제 간격 합산, 30분 초과 gap은 끊김 처리), KST 기준 날짜 집계
- Evidence Pack PDF에 일별 GPS 타임라인 섹션으로 병합

**데이터 소스**: `seed`(데모 안전망) / `web_geo`(발표용 라이브 핑) / `app`(네이티브 앱)

**테스트**: `worker/tests/test_geofence.py` (haversine 거리, IN/OUT 태깅, mocked 배제, 교차검증 match/no-match) 4 passed

---

### 테스트 현황

| 파일 | 범위 | 결과 |
|---|---|---|
| `worker/tests/test_evidence_intake.py` | 스캔/배치 등급화 (mock 분류) | passed |
| `worker/tests/test_evidence_intake_integration.py` | 오케스트레이션+규칙 통합 | 13 passed |
| `worker/tests/test_category_keywords.py` | 키워드 사전 교차검증 | passed |
| `backend/tests/test_evidence_agent_api.py` | API + HITL 불변식 | 5 passed |
| `worker/tests/test_geofence.py` | GPS 지오펜스 + 교차검증 | 4 passed |
| 디바이스 시나리오 | `node mobile/src/evidence-agent.scenario.ts` | 정상 동작 |

---

### 남은 TODO

**디바이스 (네이티브 앱)**
- Expo `expo-media-library` 갤러리 접근은 연동됨. ML Kit/TFLite 온디바이스 OCR·분류는 미연동 (현재 파일명 키워드 폴백)
- 3단계 TFLite 모델 학습·탑재 (현재 키워드 스코어 폴백)

**서버/AI**
- ✅ `PROVIDER_MODE=aws` 전환 (Terraform `worker_provider_mode=aws` 적용)
- ✅ 네이티브 앱에서 업로드 후 `/extract` 호출 추가 (`category=auto` + fire-and-forget) → Bedrock OCR 트리거
- ⏳ 배포 환경 CloudWatch Logs에서 `Bedrock 응답` 로그 실증 (구현 완료, 로그 확인 대기)

**DB**
- confidence 컬럼 Numeric→String 정렬 (잠재 지뢰)
- 모델 ↔ alembic 마이그레이션 드리프트 해소
