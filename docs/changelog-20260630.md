# 변경 이력 — 2026-06-30 (비동기 파이프라인 수정 + 검증)

> 작업자: 김재현
> 브랜치: `fix/analysis-worker-format`, `fix/pdf-ready-check`, `fix/worker-disable-xray`, `fix/pdf-font-performance`, `feature/xray-integration`, `feature/structured-logging`, `feature/row-level-auth`, `fix/issue-types-i18n`, `fix/upload-history-label`

---

## 분석 파이프라인 — 완전 비동기 전환

- `POST /analyze` → SQS 발행 후 즉시 `{"status": "analyzing"}` 응답 (Backend 블로킹 제거)
- SQS 미설정(로컬) 시 동기 실행 폴백 유지 (테스트 호환)
- FE 폴링: 5초 간격 + `pdf_ready=true`까지 대기 + 최대 3분 타임아웃
- 최초 결과 수신 시에만 scrollTo 실행 (반복 스크롤 버그 수정)
- 분석 중복 요청 방지 (`case.status == "analyzing"` 체크)

## GET /analysis API — Worker 저장 형식 호환

- Worker가 `calculation_detail`에 `report` 키 없이 저장하는 문제 대응
- `report` 키 없으면 AR 원시 데이터(wage/deduction/timeline/narrative)를 직접 구성해서 반환
- 409 에러 대신 빈 값이라도 200으로 응답 → FE 폴링 정상 동작

## PDF 다운로드 수정

- presigned URL이 evidence 버킷(`bada-dev-evidence`)을 참조하던 버그 수정
- `S3_REPORT_BUCKET` 환경변수 우선 → 미설정 시 버킷명에서 추론 (`-evidence` → `-report`)
- PDF 미생성 시 "PDF 생성 중..." 표시, `pdf_ready=true`일 때만 다운로드 버튼 노출

## PDF 생성 성능

- WeasyPrint `optimize_size=()` → WeasyPrint 63에서 미지원 확인
- `uncompressed_pdf=True` 적용 (폰트 서브셋 스킵 시도)
- 실제 병목: Fargate 0.5vCPU에서 한글 폰트(fonts-noto-cjk, 15MB) 임베딩 ~50초
- Worker CPU 상향(512→1024) 시 ~15초로 단축 가능 (인프라 작업)

## OCR 비동기 처리 (SQS → Worker)

- Backend `jobs.submit_ocr()`: ThreadPool → SQS `extract_ocr` 메시지 발행으로 전환
- Worker `_handle_ocr`: S3에서 파일 읽기 + `get_ocr().extract()` + DB 저장
- import 에러 수정: `importlib.import_module("models")` → `from app.models import Evidence`
- OCR 결과 저장 형식: `result` 전체 → `result.get("entities", result)` (내부 entities dict만)

## X-Ray SDK 통합 (#10)

- Backend: Starlette BaseHTTPMiddleware 기반 (ext.fastapi 미존재)
- `/health` 등 health check 경로 트레이싱 스킵
- `begin_segment(http=...)` → `put_http_meta()` 개별 호출로 수정
- Worker: `context_missing="IGNORE_ERROR"` (daemon sidecar 없을 때 SQS 방해 방지)
- **현재 Worker X-Ray 비활성화** — daemon sidecar 준비 후 재활성 예정

## 구조화 로깅 (#14)

- `python-json-logger` 도입
- JSON 포맷: timestamp, level, logger, service, request_id, message
- `RequestIdMiddleware`: 각 요청에 UUID 부여 → ContextVar → 로그 자동 주입
- `X-Request-ID` 응답 헤더 포함

## 행 수준 인가 (#3)

- `deps.py`에 `verify_case_owner()` 추가
- `GET /cases/{id}`: 인증 + 소유자 검증
- Evidences 5개 엔드포인트: `verify_case_owner` 적용
- 타인 사건 접근 시 403 반환

## 사건 수정/삭제 API

- `PATCH /cases/{id}`: 사건 정보 수정 (소유자만)
- `DELETE /cases/{id}`: 사건 삭제 (소유자만, 확인 Alert)

## 증거 중복 업로드 감지

- 같은 case_id + 같은 파일명 + 같은 파일 크기 → 중복으로 판단
- `{"duplicate": true}` 반환 (새 레코드 생성 안 함)

## UI 수정

- "자료 업로드 이력" → "업로드한 자료"
- "분석 보러가기" → "파일 선택 완료"
- "어려웠던 점" 항목 다국어 적용 (ISSUE_LABELS → t())
- `selectCategory` 문구 변경 (5개 언어)
- 분석 완료 시 페이지 제목 "분석 결과"로 동적 변경

## Rate Limit 상향

- 60/min → 상향 (모바일 앱 사용 패턴 대응)

---

## 발견된 이슈 및 잔여 과제

| 이슈 | 상태 | 비고 |
|------|------|------|
| PDF 내용 비어있음 | 조건부 정상 | 실제 급여명세서 이미지 업로드 시 OCR 데이터 채워져야 분석 결과 생성 |
| OCR 빈 결과 반환 | 조건부 정상 | 유의미한 데이터 없는 이미지 → 빈 entities는 정상 동작 |
| PDF 생성 50초 소요 | 미해결 | Worker CPU 상향(인프라) 또는 경량 폰트 전환 필요 |
| X-Ray Worker 비활성 | 의도적 | daemon sidecar 준비 후 consumer.py 주석 해제 |
| FE 폴링 타임아웃 3분 | 현행 유지 | OCR+분석+PDF = 2~3분. CPU 올리면 1분 이내 가능 |

---

## 테스트 가이드

정상 동작 확인을 위한 테스트 조건:
1. **실제 급여명세서/계약서 이미지** 사용 (한국어 텍스트 + 금액 포함)
2. 새 사건 생성 → 파일 업로드 → **1분 대기** (OCR 완료) → 분석 실행
3. 분석 완료 후 PDF 다운로드 확인

에뮬레이터 더미 이미지(로고, 풍경 등)로는 OCR이 엔티티를 추출하지 못해 빈 결과가 정상.
