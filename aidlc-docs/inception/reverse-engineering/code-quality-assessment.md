# Code Quality Assessment

## Test Coverage

| Area | Status | Details |
|------|--------|---------|
| **Worker Rules** | ✅ Good | 20 테스트 파일, 규칙 엔진 전체 커버 (wage, deductions, geofence, compare, legal, guardrails, confidence, chat_evidence, category_keywords) |
| **Backend API** | ⚠️ Fair | 11 테스트 파일 (API, OCR, entities, async, cognito, community, guardrails, rag, language, terminology) |
| **Integration** | ⚠️ Fair | evidence_intake_integration, ci.yml로 자동 실행 |
| **E2E** | ❌ None | End-to-end 테스트 없음 |
| **Frontend** | ❌ None | JS 테스트 없음 |
| **Infrastructure** | ❌ None | Terraform plan만 사용, 자동화된 infra 테스트 없음 |
| **Overall** | ⚠️ Fair | 규칙 엔진은 우수, API/서비스 레이어는 부분적 |

## Code Quality Indicators

| Indicator | Status | Details |
|-----------|--------|---------|
| **Linting** | ❌ Not configured | pylint/flake8/ruff 설정 없음 |
| **Type Checking** | ⚠️ Partial | Type hints 사용하나 mypy 설정 없음 |
| **Code Style** | ✅ Consistent | 일관된 명명, 한국어 주석, docstring 사용 |
| **Documentation** | ✅ Good | 각 모듈 상단 docstring, steering 규칙 문서 풍부 |
| **Error Handling** | ✅ Good | errors.py 글로벌 핸들러, worker에서 try/except + DLQ |
| **Security** | ⚠️ Fair | PII masking 존재, 그러나 CORS allow_origins=["*"] |
| **Logging** | ✅ Good | 구조화 로그 (name, level, message), CloudWatch 연동 |

## Technical Debt

| Issue | Location | Severity | Notes |
|-------|----------|----------|-------|
| CORS `allow_origins=["*"]` | `backend/app/main.py` | Medium | 프로덕션에서 도메인 제한 필요 |
| `AUTH_MODE=demo` 운영 | 배포 환경 | High | Cognito 연동 완료 전까지 인증 우회 상태 |
| `database_auto_create=True` | 배포 환경 | Medium | Alembic 마이그레이션으로 전환 필요 |
| Worker analysis handler HTTP 호출 | `worker/handlers/analysis.py` | Low | 1단계 전략(설계상 의도), 2단계에서 직접 DB 접근 전환 예정 |
| Transcription handler 미구현 | `worker/handlers/transcription.py` | Medium | `NotImplementedError` raise |
| Frontend Next.js 미구현 | `frontend/` | Medium | Static HTML로 대체 운영 중 |
| ALB HTTPS 미적용 | `infra/main.tf` | High | ACM 인증서 + HTTPS listener 필요 |
| JWT secret 하드코딩 기본값 | `backend/app/config.py` | High | `"dev-insecure-change-me"` — 반드시 .env 교체 |
| WeasyPrint PDF 미검증 | `backend/app/services/report_builder.py` | Medium | 다국어 폰트 렌더링 실제 검증 필요 |
| 평가셋 실행 미검증 | `eval/` | Low | CI에서 실행하나 실제 정확도 수치 미확인 |

## Patterns and Anti-patterns

### Good Patterns ✅
- **규칙/LLM 분리**: 계산·판정은 규칙 코드, 문장화만 LLM — 설명 가능성 확보
- **Provider 추상화**: `PROVIDER_MODE` 환경변수로 Mock↔AWS 즉시 전환
- **단일 인증 seam**: `deps.py:get_current_user` 한 곳에서 인증 전략 교체
- **멱등성 설계**: Worker consumer는 메시지 중복 수신에 안전
- **Guardrails**: LLM 출력 금지 표현 차단 + 숫자 환각 감지
- **Structured output**: Pydantic 스키마로 LLM 출력 강제
- **DLQ 패턴**: 실패 메시지 격리, 무한 재시도 방지
- **Human-in-the-loop**: confidence=low 항목은 사용자 확인 유도

### Anti-patterns / Improvement Areas ⚠️
- **Fat Router**: `kakao.py` (38KB), `evidences.py` (15KB) — 서비스 레이어로 추출 권장
- **직접 DB 쿼리 in Router**: Repository 패턴 미적용, 라우터에서 SQLAlchemy 직접 사용
- **정적 파일 서빙**: Backend가 Frontend 정적 파일도 서빙 (배포 시 CloudFront/S3 분리 권장)
- **환경변수 폭발**: config.py에 50+ 환경변수 — 그룹화/계층화 부족
- **테스트 격리**: 일부 테스트가 실제 외부 서비스에 의존할 수 있음 (Mock 불완전)

## Architecture Decision Records (Implicit)

| Decision | Rationale | Documented In |
|----------|-----------|--------------|
| 규칙/LLM 분리 | "AI가 금액을 잘못 계산하면?" 대응 | architecture.md |
| 단일 워커 순차 실행 | Step Functions 대신 5주 MVP 단순화 | tech.md |
| NAT Gateway 미사용 | 비용 절감 ($45/월) | tech.md |
| Claude Vision for OCR | Textract 한국어 미지원 | tech.md |
| WeasyPrint for PDF | 다국어 합자 렌더링 (ReportLab 대비) | tech.md |
| Static Frontend | Next.js 전환 계획 있으나 MVP는 Vanilla JS | OWNERSHIP.md |
