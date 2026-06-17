## GPS 기능 브리핑

---

### 목적

재직 중(분쟁 전)부터 출퇴근 위치를 자동 수집 → 분쟁 시 "이 날 이 시간에 근무지에 있었다"는 정황 증거. 카톡 도착 발화와 교차검증해 신빙성 강화.

---

### 사용자 흐름

```
① 사건 정보 입력
   - 사업장명
   - 근무지 위치: 주소 검색 / 현재위치 버튼 / 좌표 직접입력
   - 인정 반경: 슬라이더 50~500m (기본 100m). 농장·건설현장은 넓게.
   → "다음: 자료 올리기" 클릭 시 사건 생성 + 근무지 자동 등록

② 홈 화면 GPS 스위치 ON
   → 30초마다 핑 자동 전송
   → 근무지 반경 이내 = IN_WORKPLACE / 초과 = OUTSIDE

③ 증거 업로드 → "GPS 정황 포함" 체크
   → "등록된 근무지: 37.xxx, 126.xxx (반경 100m)" 자동 표시
   → "현재 N건 수집됨" 표시
   → 수동 입력 불필요 (DB에서 자동 수집)

④ Evidence Pack 분석
   → GPS 정황: 일별 요약 + 교차검증 결과 포함
   → 결과 화면: 날짜별 근무지 핑·체류시간 테이블
   → PDF 리포트: 동일 GPS 섹션 출력
```

---

### 서버 엔드포인트

| 메서드 | 경로 | 역할 |
|---|---|---|
| POST | `/cases/{id}/gps/workplace` | 근무지(지오펜스) 등록 |
| GET | `/cases/{id}/gps/workplace` | 등록된 근무지 조회 |
| POST | `/cases/{id}/gps/ping` | GPS 좌표 수신 + IN/OUT 판정 |
| GET | `/cases/{id}/gps/logs` | 핑 로그 전체 조회 |
| GET | `/cases/{id}/gps/summary` | 일별 요약 (Evidence Pack용) |

---

### 핑 판정

- Haversine 거리 ≤ `radius_m` → IN_WORKPLACE
- 초과 → OUTSIDE
- 근무지 미등록 → UNKNOWN
- `is_mocked = true` → status = null, 자동 배제
- 서버 vs 기기 시각 > 60초 → `is_delayed_upload = true`, 교차검증 배제 + 경고 배지

---

### 무결성 체인

- 매 핑마다 `SHA-256(이전_hash | ts | lat | lng | status)` 계산
- 중간 DB 조작 시 이후 체인 전부 깨져 탐지 가능
- Evidence Pack 하단에 전체 GPS 해시 + 생성 시각 삽입

---

### 일별 요약 (규칙 기반, LLM 미사용)

1. KST 날짜 기준 그룹핑
2. mocked·지연업로드 핑 배제
3. IN_WORKPLACE 핑만 시간순 정렬
4. 체류시간 = IN 핑 간 간격 합산 (30분 초과 갭은 미산입)
5. 출력: 날짜 / IN 핑 수 / OUT 핑 수 / 최초·최종 체류 시각 / 추정 체류시간

---

### 카톡 교차검증

- `cross_check(tagged_logs, chat_arrivals, window_min=30)`
- ±30분 안에 IN_WORKPLACE 핑 + 카톡 도착 발화 → "정황 일치"
- 불일치도 집계 (도착 발화만 있고 핑 없음)
- 일치·불일치 카운트 모두 결과에 노출

---

### 근무지 주소 검색

- 카카오 Places 키워드 검색 → 실패 시 Geocoder 주소 검색 폴백
- 결과 클릭 → 좌표 자동 입력 + 사업장명 비었으면 채움
- 카카오 SDK 미로드 시 안내 메시지 + 좌표 직접입력 폴백
- **주의**: `localhost:8000`으로 접속해야 카카오 동작 (`127.0.0.1`은 도메인 불일치로 차단)

---

### 인증

- gps.js의 모든 API 호출에 `_gpsHeaders()` → JWT 토큰 자동 첨부
- 미첨부 시 데모유저로 처리 → 사건 소유자 불일치 → 404

---

### 파일 구조

| 파일 | 역할 |
|---|---|
| `backend/app/routers/gps.py` | 5개 엔드포인트 + Haversine + chain_hash |
| `backend/app/models.py` | GpsLog, Workplace ORM |
| `backend/app/schemas_report.py` | Gps, GpsDaySummary 스키마 |
| `backend/app/services/report_builder.py` | GPS → 표준 리포트 매핑 |
| `backend/app/routers/analysis.py` | report.html GPS 일별 테이블 |
| `backend/app/services/analysis_service.py` | ctx에 GPS 핑·근무지 주입 |
| `backend/app/static/js/gps.js` | 토글·핑전송·근무지등록·주소검색·정보표시·결과지도 |
| `backend/app/static/js/analysis.js` | 분석 시 DB GPS 자동 수집 + 결과 화면 일별 테이블 |
| `worker/rules/geofence.py` | tag_logs + cross_check + summarize_by_day |
| `worker/pipeline.py` | GPS 단계 (태깅 → 교차검증 → 일별 요약) |

---

### DB 테이블

**gps_logs**: id, case_id(FK), ts, lat, lng, status, is_mocked, is_delayed_upload, source, chain_hash, prev_chain_hash, server_ts

**workplaces**: id, case_id(FK), center_lat, center_lng, radius_m (50~500, 기본 100)

---

### 핑 주기

- 데모: 30초
- 운영: 5분 (전환 시 `GPS_PING_INTERVAL` 변경)
