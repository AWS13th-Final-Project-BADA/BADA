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

---

# 변경 이력 — 2026-06-30 오후 (OCR 파이프라인 근본 수정 + 성능 개선)

> 작업자: 김재현, 이동규
> 브랜치: `fix/ocr-exclude-audio`, `fix/worker-prompts-missing`, `fix/ocr-flat-entities`, `perf/ocr-1pass-restore`, `infra/worker-cpu-upgrade`
> PR: #139, #143, #144, #149, #150, #151, #152

---

## OCR entities 빈 값 근본 원인 해결

### 문제 현상
- Claude Vision이 `raw_text`는 완벽하게 추출하면서 `entities`(hourly_wage, amounts 등)를 전부 null/빈 배열로 반환
- 모든 카테고리(contract, chat, other)에서 동일 증상
- PDF에 데이터 없음, 급여 분석 0원

### 근본 원인
**Worker Dockerfile에 `prompts/` 디렉토리 미포함** (PR #144)

```dockerfile
# 누락됐던 라인
COPY prompts /app/prompts
```

- `extraction.md` 프롬프트 파일이 Docker 이미지에 없어서 `_instruction()`이 항상 except fallback(한 줄짜리 간략 프롬프트)으로 동작
- 간략 프롬프트로는 LLM이 entities를 채우지 않음
- **6월 5일 entities 구조화 도입 이후 지금까지 프롬프트가 한 번도 제대로 로드된 적 없었음**

### 해결
- `COPY prompts /app/prompts` 추가 → extraction.md 정상 로드
- extraction.md에 "entities 빈 값 금지" 절대 규칙 추가
- chat/other 카테고리 전용 프롬프트 신규 작성

---

## OCR 음성 파일(audio) 제외 필터 (PR #139)

### 문제
- Worker `_handle_ocr`에서 `file_type` 필터 없이 모든 pending/processing 증거를 Claude Vision에 전송
- `.wav` 음성 파일 → Bedrock `ValidationException: Could not process image`

### 수정
```python
# 변경 전
evidences = session.query(Evidence).filter(
    Evidence.case_id == case_id,
    Evidence.ocr_status.in_(["pending", "processing"])
).all()

# 변경 후
evidences = session.query(Evidence).filter(
    Evidence.case_id == case_id,
    Evidence.file_type.in_(["image", "pdf"]),  # audio 제외
    Evidence.ocr_status.in_(["pending", "processing"])
).all()
```

- audio는 업로드 시 `transcribe` 메시지로 별도 라우팅되므로 OCR에서 제외하는 것이 정상 설계

---

## OCR flat JSON 응답 흡수 (PR #150, 이동규)

- LLM이 `entities` 래핑 없이 flat하게 줄 때(`{"raw_text": "...", "hourly_wage": 10030}`) 정규화
- `raw_text` 외 필드를 `entities`로 감싸서 OcrResult 검증 통과
- schema.py에 문자열 필드에 dict 올 때 대표값 추출 validator 추가

---

## OCR 1-pass 복귀 (PR #152)

### 변경
```
변경 전 (2-pass): 이미지 → Vision(텍스트) → Text(구조화) → 2회 Bedrock 호출, ~40초
변경 후 (1-pass): 이미지 → Vision(raw_text + entities JSON) → 1회 Bedrock 호출, ~20초
```

### 안전한 이유
- `prompts/extraction.md`가 Docker에 포함됨 (PR #144)
- flat JSON 응답도 `_bedrock.py`에서 정규화 (PR #150)
- extraction.md에 entities 필수 추출 절대 규칙 추가됨

### 효과
- 증거 1건당 Bedrock 호출 2회 → 1회, **~20초 절약**

---

## Worker CPU/Memory 상향 (PR #149, #151)

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| CPU | 256 units (0.25 vCPU) | 1024 units (1 vCPU) |
| Memory | 512 MiB | 2048 MiB |

- PDF 생성(WeasyPrint 한글 폰트 임베딩)이 CPU-bound → CPU 4배로 ~50초 → ~12-15초 단축 기대
- 비용: desired=1 기준 약 +$8/2주
- 산정 근거 문서: `docs/infra/worker-cpu-sizing.md`

---

## i18n: upload.categories.auto 번역 키 추가

- 자동 분류(`auto`) 카테고리로 저장된 증거가 업로드 이력에 표시될 때 `[missing translation]` 발생
- 5개 언어(ko/en/vi/km/ja) 전부 추가

---

## 성능 개선 전후 비교 (증거 1건 기준, 예상치)

| 단계 | 변경 전 | 변경 후 | 비고 |
|------|---------|---------|------|
| OCR (Bedrock) | ~40초 (2회) | ~20초 (1회) | 1-pass 복귀 |
| 분석 LLM | ~5초 | ~5초 | 변동 없음 |
| PDF 생성 | ~50초 | ~12-15초 | CPU 상향 |
| **합계** | **~95초** | **~37-40초** | **55~60% 단축** |

---

## 발견된 이슈 업데이트

| 이슈 | 상태 | 비고 |
|------|------|------|
| OCR entities 빈 값 | **해결** | Dockerfile prompts/ 추가 + 프롬프트 강화 |
| 음성 파일 OCR 에러 | **해결** | file_type 필터 추가 |
| PDF 생성 50초 소요 | **해결 예정** | CPU 상향 PR 머지됨, terraform apply 대기 |
| 급여 분석 0원 | 정상 동작 | 근무시간(schedule) 증거 없으면 계산 불가. 시급/공제는 정상 추출됨 |
| 1-pass 안정성 | 모니터링 | entities 빈 값 재발 시 2-pass 롤백 |
