## 증거 수집 에이전트 — 구현 현황 총정리

---

### 목적

사용자가 파일을 일일이 찾아 올리는 대신, 디바이스 갤러리에서 증거를 **자동 탐색·분류·추천**한다. AI는 추천만, 최종 등록은 사용자 승인(HITL).

---

### 4단계 파이프라인

| 단계 | 위치 | 동작 | 비용 |
|---|---|---|---|
| 1 메타데이터 필터 | 디바이스 | 근무기간 내 + 스크린샷/카톡/다운로드/카메라 + 10KB↑ + 이미지/PDF | 0원 |
| 2 온디바이스 OCR + 키워드 | 디바이스 | ML Kit/Vision 텍스트 추출 → "급여/임금/계약/입금/체불" 키워드 2개↑ | 0원 |
| 3 경량 모델 분류 | 디바이스 | TFLite/CoreML (현재는 키워드 수 폴백) | 0원 |
| 4 서버 분류·OCR·저장 | 서버 | Bedrock/Upstage로 정밀 추출 + DB 저장 | ~30원/건 |

사용자 승인(HITL) = 3단계 후. recommend/maybe 표시 → 사용자 선택 → 4단계 진입.

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

### 프론트 UI (upload.js)

- **에이전트 스캔 카드** (보라색) — 파일 선택 → 동의 모달 → /scan → 추천 카드 렌더
- **추천 카드** — 파일별 체크박스 + decision(추천/확인필요/제외) + 이유 표시
- **"선택한 파일 등록" 버튼** → `/agent-upload` → 자동 extract 시작
- **제외 되살리기** — 제외된 파일에 "되살리기" 버튼 → `/restore` → 재추출
- **동의 모달** (PIPA) — 파일 접근 전 사용자 동의. "본인 자료만", "증거 정리 목적", "자동등록 안 함" 고지

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

### 디바이스 코드 (mobile/src/)

| 파일 | 역할 |
|---|---|
| `evidence-agent.ts` | 4단계 파이프라인 (1~3단계 디바이스 로직 + uploadApproved/triggerExtract) |
| `evidence-agent.scenario.ts` | Node.js 시나리오 데모 (AWS 불필요) |

현재 `ocrFn`, `classifyFn` 콜백은 스텁 — 네이티브 앱 빌드 시 실제 ML Kit/TFLite에 연결 필요.

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

이건 바로 위에서 별도 브리핑했으니 요약만:
- 사건 생성 시 근무지 등록 (주소 검색/현재위치/좌표 직접입력, 반경 50~500m)
- 홈 GPS 스위치 → 30초마다 핑 수집 → IN/OUTSIDE 판정
- 분석 시 DB에서 자동 수집 → 일별 요약 + 카톡 교차검증 → Evidence Pack 반영

---

### 테스트 현황

| 파일 | 범위 | 결과 |
|---|---|---|
| `worker/tests/test_evidence_intake_integration.py` | 오케스트레이션+규칙 통합 | 13 passed |
| `backend/tests/test_evidence_agent_api.py` | API + HITL 불변식 | 5 passed |
| `worker/tests/test_geofence.py` | GPS 지오펜스 + 교차검증 | 4 passed |
| 디바이스 시나리오 | `node mobile/src/evidence-agent.scenario.ts` | 정상 동작 |

---

### 남은 TODO

**디바이스 (네이티브 앱)**
- Capacitor 갤러리 접근 플러그인 연동
- ocrFn/classifyFn 실제 네이티브 브릿지 연결
- 3단계 TFLite 모델 학습·탑재 (현재 키워드 폴백)

**서버/AI**
- `PROVIDER_MODE=aws` 전환 → Bedrock OCR 실증

**DB**
- confidence 컬럼 Numeric→String 정렬 (잠재 지뢰)
- 모델 ↔ alembic 마이그레이션 드리프트 해소
