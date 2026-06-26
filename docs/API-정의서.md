# BADA API 정의서

> 최종 갱신: 2026-06-26
> Base URL: `https://api.badasoft.com` (운영) / `http://localhost:8000` (로컬)
> 인증: `Authorization: Bearer {jwt}` (별도 표기 없으면 인증 필수)

---

## 인증 (Auth)

### `GET /auth/{provider}/login`

소셜 로그인 시작. provider의 OAuth authorize 페이지로 302 리다이렉트.

| 항목 | 값 |
|------|---|
| provider | `google` / `kakao` / `naver` |
| Query | `redirect_uri` (선택) — 콜백 후 돌아갈 앱 딥링크 |
| 인증 | 불필요 |
| 응답 | 302 Redirect → provider authorize URL |

### `GET /auth/{provider}/callback`

OAuth 콜백 수신. JWT 발급 후 앱으로 리다이렉트.

| 항목 | 값 |
|------|---|
| Query | `code` (필수), `state`, `error`, `error_description` |
| 인증 | 불필요 |
| 응답 | 302 → `bada://auth?token={jwt}` 또는 `{app_base_url}/#token={jwt}` |

### `GET /auth/cognito/login`

Cognito Hosted UI 리다이렉트 (레거시).

| Query | `identity_provider` (선택), `prompt` (선택), `redirect_uri` (선택) |
|-------|---|
| 응답 | 302 → Cognito authorize URL |

### `GET /auth/cognito/callback`

| Query | `code`, `state`, `error` |
|-------|---|
| 응답 | 302 → 앱/웹으로 토큰 전달 |

### `GET /auth/me`

현재 로그인 유저 정보.

| 응답 |
|------|
```json
{ "id": "uuid", "email": "...", "name": "...", "preferred_lang": "ko", "provider": "google" }
```

### `POST /auth/kakao/link-code`

카카오 채널 연동용 6자리 코드 발급.

| 응답 |
|------|
```json
{ "code": "A3B7K9", "guide": "Send this code to the BADA Kakao channel to link your account." }
```

### `POST /auth/logout`

| 응답 | `{ "ok": true }` |
|------|---|

---

## 사건 (Cases)

### `POST /cases`

새 사건 생성.

| Body (JSON) | 타입 | 필수 | 설명 |
|-------------|------|:----:|------|
| workplace_name | string | — | 사업장 이름 |
| employer_name | string | — | 사업주 이름 |
| work_start_date | date | — | 근무 시작일 (YYYY-MM-DD) |
| work_end_date | date | — | 근무 종료일 |
| agreed_hourly_wage | int | — | 약속 시급 (원) |
| agreed_weekly_hours | float | — | 주간 근무시간 |
| issue_types | string[] | — | 문제 유형 목록 |

**응답** (201):
```json
{
  "id": "uuid",
  "workplace_name": "...",
  "employer_name": "...",
  "work_start_date": "2025-01-15",
  "work_end_date": null,
  "agreed_hourly_wage": 9860,
  "agreed_weekly_hours": 40.0,
  "issue_types": ["임금체불"],
  "status": "open"
}
```

### `GET /cases`

내 사건 목록 (본인 user_id 필터, 최신순).

**응답**: Case 배열

### `GET /cases/{case_id}`

사건 상세 조회.

> ⚠️ 현재 인가 미적용 — 타인 사건도 조회 가능 (#3 미구현)

---

## 증거 (Evidences)

### `POST /cases/{case_id}/evidences/upload`

파일 업로드.

| Form Field | 타입 | 필수 | 설명 |
|-----------|------|:----:|------|
| category | string | O | contract/schedule/payment/chat/statement/other |
| file | File | O | 업로드 파일 |

**응답**: Evidence 객체 (id, category, s3_key, ocr_status)

### `POST /cases/{case_id}/evidences/request-upload`

Presigned S3 URL 발급.

| Body | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| file_name | string | O | 파일명 |
| file_type | string | O | image/pdf/text |
| category | string | O | 카테고리 |
| content_type | string | — | MIME 타입 |

**응답**: `{ "upload_url": "...", "s3_key": "...", "evidence_id": "..." }`

### `POST /cases/{case_id}/evidences/scan`

여러 이미지 빠른 분류 (OCR 없음).

| Body | 타입 | 설명 |
|------|------|------|
| files | File[] | 이미지 파일들 (multipart) |

**응답**: 분류 결과 배열 `[{ filename, category, confidence }]`

### `POST /cases/{case_id}/evidences/assess`

1장 정밀 분석 (분류 + OCR + 키워드 검증).

| Body | 타입 | 설명 |
|------|------|------|
| file | File | 이미지 1장 |

**응답**: `{ category, confidence, entities, cross_validation }`

### `POST /cases/{case_id}/evidences/add-manual`

텍스트 수동 입력 증거.

| Body | 타입 | 설명 |
|------|------|------|
| category | string | 카테고리 |
| text | string | 내용 |

### `POST /cases/{case_id}/extract`

모든 증거 OCR/엔티티 추출 실행.

| Query | `wait` (bool, 선택) — true면 동기 대기 |
|-------|---|

### `GET /cases/{case_id}/extract-status`

추출 진행 상태.

**응답**: `{ "total": 5, "done": 3, "pending": 2, "failed": 0 }`

### `PATCH /cases/{case_id}/evidences/{eid}/entities`

OCR 결과 수동 수정.

| Body | 타입 | 설명 |
|------|------|------|
| entities | object | 수정된 엔티티 JSON |

### `POST /cases/{case_id}/evidences/{eid}/restore`

제외된 증거 복원.

### `GET /cases/{case_id}/evidences`

증거 목록 조회.

### `DELETE /cases/{case_id}/evidences/{eid}`

증거 삭제.

---

## 분석 (Analysis)

### `POST /analysis/{case_id}`

분석 실행 트리거.

| Query | 타입 | 설명 |
|-------|------|------|
| lang | string | 대상 언어 (기본: ko) |

| Body (선택) | 타입 | 설명 |
|------------|------|------|
| agreed_hourly_wage | int | 수동 시급 (OCR 값 override) |
| worked_hours | float[] | 수동 근무시간 |
| deposits | [{date, amount}] | 수동 입금 내역 |
| deductions | [{name, amount}] | 수동 공제 내역 |

**동작**: 운영(SQS 설정됨) → 비동기 Worker 실행 / 로컬(SQS 미설정) → 동기 실행

### `GET /analysis/{case_id}`

분석 결과 조회.

**응답**:
```json
{
  "total_expected_wage": 1580000,
  "total_received_wage": 1200000,
  "suspected_unpaid": 380000,
  "deduction_items": [...],
  "calculation_detail": "...",
  "timeline_summary": "...",
  "missing_evidences": [...]
}
```

### `GET /analysis/{case_id}/timeline`

타임라인 이벤트 목록.

**응답**: `[{ type, title, description, description_translated, event_date, confidence }]`

### `GET /analysis/{case_id}/pairs`

번역 대조표.

**응답**: `[{ source_text, translated_text, evidence_type, related_issue }]`

### `GET /analysis/{case_id}/missing`

누락 증거 목록.

**응답**: `[{ category, importance, guide }]`

### `GET /analysis/{case_id}/report`

HTML 보고서 (임금체불 정밀 분석 리포트).

| Query | lang (기본: ko) |
|-------|---|
| 응답 | HTML |

### `GET /analysis/{case_id}/report/pdf`

PDF Evidence Pack 다운로드.

| Query | lang (기본: ko) |
|-------|---|
| 응답 | application/pdf |

---

## GPS 근무 증거

### `POST /gps/{case_id}/workplace`

직장 위치 등록.

| Body | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| lat | float | O | 위도 |
| lng | float | O | 경도 |
| radius_m | int | — | 인정 반경 (기본: 50m) |

### `GET /gps/{case_id}/workplace`

직장 정보 조회.

### `POST /gps/{case_id}/ping`

GPS 핑 수신.

| Body | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| lat | float | O | 위도 |
| lng | float | O | 경도 |
| ts | datetime | O | 측정 시각 (ISO 8601) |
| is_mocked | bool | — | GPS 위조 여부 |
| is_delayed_upload | bool | — | 지연 업로드 여부 |

**응답**:
```json
{ "status": "IN_WORKPLACE", "distance_m": 23.4, "chain_hash": "abc123..." }
```

### `GET /gps/{case_id}/logs`

GPS 로그 목록.

### `GET /gps/{case_id}/summary`

일별 출근 요약.

**응답**: `[{ date, in_count, out_count, excluded_count }]`

---

## AI 채팅 (Chat)

### `POST /chat/messages`

AI 상담 메시지 전송.

| Body | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| message | string | O | 질문 텍스트 |
| case_id | string | — | 연결할 사건 ID (맥락 반영) |
| language | string | — | 응답 언어 (auto면 자동 감지) |
| session_id | int | — | 채팅 세션 ID |

**응답**:
```json
{
  "answer": "임금체불 신고는 관할 노동청에...",
  "intent": "procedure_inquiry",
  "risk_level": "safe",
  "ai_provider": "bedrock",
  "used_case_context": true,
  "used_rag": true,
  "guardrail_result": "passed",
  "fallback_used": false,
  "sources": [{ "title": "...", "source_org": "고용노동부", "section": "..." }],
  "next_actions": ["관할 노동청 찾기", "진정서 양식 확인"],
  "disclaimer": "본 정보는 법률 자문이 아닙니다..."
}
```

---

## 카카오 챗봇 (Kakao)

### `POST /kakao/skill`

카카오 채널 스킬 웹훅.

| 인증 | 불필요 (카카오 서버에서 직접 호출) |
|------|---|
| Body | 카카오 스킬 JSON 표준 포맷 |
| 응답 | 카카오 스킬 응답 (SimpleText / Carousel / QuickReply) |

---

## 커뮤니티 (Community)

### 게시글

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/community/posts` | 목록 (query: category, sort, language, q, mine, limit) |
| POST | `/community/posts` | 작성 (body: title, body, category, language) |
| GET | `/community/posts/{id}` | 상세 |
| PATCH | `/community/posts/{id}` | 수정 |
| DELETE | `/community/posts/{id}` | 삭제 (soft) |

### 댓글

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/community/posts/{id}/comments` | 댓글 목록 (query: limit) |
| POST | `/community/posts/{id}/comments` | 댓글 작성 (body: body) |
| GET | `/community/comments/{id}` | 댓글 조회 |
| PATCH | `/community/comments/{id}` | 수정 |
| DELETE | `/community/comments/{id}` | 삭제 (soft) |

### 상호작용

| 메서드 | 경로 | Body | 설명 |
|--------|------|------|------|
| POST | `/community/reactions` | { target_type, target_id, reaction_type } | 좋아요/저장 토글 |
| POST | `/community/translate` | { target_type, target_id, target_language } | 번역 |
| POST | `/community/reports` | { target_type, target_id, reason, description } | 신고 |
| GET | `/community/reports` | query: status, limit | 신고 목록 (관리) |
| PATCH | `/community/reports/{id}` | { status } | 신고 상태 변경 |
| POST | `/community/safety-check` | { content, language } | 콘텐츠 안전 검사 |
| GET | `/community/boards` | — | 게시판 카테고리 요약 |

---

## 시스템 (System)

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|:----:|------|
| GET | `/health` | X | `{ "status": "ok" }` |
| GET | `/health/db` | X | DB 연결 확인 |
| GET | `/version` | X | `{ "name", "version", "auth_mode", "storage_mode" }` |
| GET | `/metrics` | X | Prometheus 메트릭 (text/plain) |
| GET | `/` | X | 앱 다운로드 안내 페이지 (static HTML) |

---

## 에러 응답 형식

```json
{
  "detail": "에러 메시지 (한국어)"
}
```

| HTTP Code | 의미 |
|-----------|------|
| 400 | 잘못된 요청 (파라미터 누락/형식 오류) |
| 401 | 인증 실패 (토큰 만료/미제공) |
| 404 | 리소스 없음 |
| 429 | Rate Limit 초과 (60req/min) |
| 500 | 서버 내부 오류 |
| 502 | 외부 서비스 오류 (OAuth, Transcribe 등) |
| 503 | 서비스 미설정 (provider not configured) |

### Rate Limit 헤더

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1719388800
```
