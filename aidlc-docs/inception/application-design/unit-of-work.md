# 유닛 정의서

## 실행 전략
- **순서**: 순차 실행 (유닛 1 → 2 → 3 → 4 → 5 → 6)
- **동기 분석**: 유지 (Backend 간단 분석 + Worker 전체 파이프라인 병행)
- **Static HTML**: Frontend ECS 배포 완료 시 제거

---

## 유닛 1: 인프라 및 보안

| 항목 | 내용 |
|------|------|
| **우선순위** | P0 |
| **범위** | HTTPS, 보안 미들웨어, CORS, ALB 로깅, Worker 기동, Frontend ECS 기반 준비 |
| **산출물** | Terraform 변경 (ACM, HTTPS listener, 호스트 라우팅, Frontend ECR/ECS/TG, Worker desired=1), Backend 보안 미들웨어 (헤더, Rate limit, CORS 도메인 제한) |
| **변경 대상** | `infra/main.tf`, `infra/variables.tf`, `backend/app/main.py`, 신규 미들웨어 파일 |
| **완료 기준** | ALB HTTPS 동작, 보안 헤더 응답, CORS 제한 확인, Worker ECS running=1 |

---

## 유닛 2: 인증

| 항목 | 내용 |
|------|------|
| **우선순위** | P0 |
| **범위** | Cognito JWKS 토큰 검증, 카카오/구글 소셜 로그인 완성, AUTH_MODE=cognito 전환 |
| **산출물** | Backend deps.py Cognito 검증 로직, 소셜 로그인 콜백 완성, Cognito callback/logout URL 업데이트(HTTPS 도메인) |
| **변경 대상** | `backend/app/deps.py`, `backend/app/services/cognito_auth_service.py`, `backend/app/routers/auth.py`, Terraform (Cognito callback URL) |
| **의존성** | 유닛 1 (HTTPS 도메인 필요) |
| **완료 기준** | Cognito 로그인 → 토큰 발급 → API 호출 성공, 카카오/구글 로그인 동작 |

---

## 유닛 3: Worker 파이프라인

| 항목 | 내용 |
|------|------|
| **우선순위** | P0 |
| **범위** | Worker DB 직접 접근(2단계), 전체 분석 파이프라인 E2E, STT(Transcribe) 구현, Bedrock 실제 호출 검증 |
| **산출물** | Worker `db.py`, `handlers/analysis.py` 2단계 전환, `handlers/transcription.py` 구현, Bedrock/Translate 연동 검증 |
| **변경 대상** | `worker/handlers/analysis.py`, `worker/handlers/transcription.py`, `worker/db.py`(신규), `worker/Dockerfile` |
| **의존성** | 유닛 1 (Worker ECS 기동, DATABASE_URL Secret 주입) |
| **완료 기준** | SQS 메시지 → Worker 분석 완료 → DB 저장 확인, Transcribe 전사 동작 |

---

## 유닛 4: PDF 생성

| 항목 | 내용 |
|------|------|
| **우선순위** | P1 |
| **범위** | WeasyPrint Evidence Pack 렌더, 다국어 폰트 임베딩, S3 저장 |
| **산출물** | `worker/services/pdf_generator.py`, HTML/CSS 템플릿, Dockerfile 폰트 설치, PDF 생성 → S3 업로드 |
| **변경 대상** | `worker/services/pdf_generator.py`(신규), `worker/Dockerfile`, HTML 템플릿 파일 |
| **의존성** | 유닛 3 (분석 결과 데이터가 있어야 PDF 생성 가능) |
| **완료 기준** | 분석 완료 후 PDF 생성 → S3 저장 → 다운로드 가능, 한국어+베트남어 렌더 정상 |

---

## 유닛 5: Frontend (Next.js)

| 항목 | 내용 |
|------|------|
| **우선순위** | P1 |
| **범위** | Next.js 15 App Router, Tailwind, next-intl(ko/vi/en), 모든 화면, ECS 배포, Backend Static 제거 |
| **산출물** | `frontend/` Next.js 프로젝트, Dockerfile, CI/CD workflow, 화면 (로그인/사건/업로드/결과/GPS/커뮤니티/챗봇) |
| **변경 대상** | `frontend/`(전체 재작성), `.github/workflows/deploy-dev-frontend.yml`(신규), `backend/app/main.py`(static 제거) |
| **의존성** | 유닛 2 (인증 동작해야 프론트 로그인 가능) |
| **완료 기준** | ECS 배포, bada.kr 접속, 로그인→사건생성→업로드→분석→결과 확인 E2E 동작 |

---

## 유닛 6: PBT 및 품질

| 항목 | 내용 |
|------|------|
| **우선순위** | P1 |
| **범위** | Hypothesis 도입, 규칙엔진(wage/deductions/geofence/compare/guardrails) PBT 작성, CI 통합 |
| **산출물** | `worker/tests/test_pbt_*.py`, `requirements.txt`에 hypothesis 추가, CI workflow PBT 단계 |
| **변경 대상** | `worker/tests/`(신규 PBT 파일), `worker/requirements.txt`, `.github/workflows/ci.yml` |
| **의존성** | 유닛 3 (Worker 규칙엔진 안정화 후 PBT 적용) |
| **완료 기준** | PBT 전체 통과, CI에서 시드 기록, shrinking 동작 확인 |
