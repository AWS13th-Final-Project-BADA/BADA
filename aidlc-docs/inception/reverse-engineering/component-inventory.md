# Component Inventory

## Application Packages

| Package | Purpose | Status |
|---------|---------|--------|
| `backend/` | FastAPI REST API 서버 (인증, CRUD, OCR, 분석, 챗봇, GPS, 커뮤니티) | ✅ 실행 중 |
| `worker/` | SQS 비동기 분석 워커 (규칙 엔진 + LLM 보조) | ⚠️ 코드 완성, 미기동 |
| `frontend/` (계획) | Next.js + next-intl 프론트엔드 (미구현, README만 존재) | ❌ 미구현 |
| `backend/app/static/` | Vanilla JS SPA 프론트엔드 (실제 사용 중) | ✅ 운영 중 |
| `mobile/` | Capacitor 네이티브 앱 래퍼 (레거시, 전환 완료) | 🔒 이력 보존 |
| `mobile-native/` | React Native + Expo 네이티브 앱 (SDK 51, expo-router) | ✅ M1~M3 완료 |

## Infrastructure Packages

| Package | Type | Purpose | Status |
|---------|------|---------|--------|
| `infra/` | Terraform | AWS 전체 인프라 (VPC, ECS, RDS, S3, SQS, Cognito, CloudWatch) | ✅ 적용 완료 |
| `.github/workflows/deploy-dev.yml` | GitHub Actions | Backend 자동배포 (ECR → ECS) | ✅ 동작 |
| `.github/workflows/deploy-dev-worker.yml` | GitHub Actions | Worker 자동배포 (ECR → ECS) | ✅ 동작 |
| `.github/workflows/rollback-dev-backend.yml` | GitHub Actions | Backend 수동 롤백 | ✅ 준비 |
| `.github/workflows/ci.yml` | GitHub Actions | 테스트 자동 실행 | ✅ 동작 |

## Shared Packages

| Package | Type | Purpose |
|---------|------|---------|
| `prompts/` | 템플릿 | LLM 프롬프트 (extraction, classification, timeline, summary) |
| `frontend/locales/` | i18n JSON | 다국어 번역 키 (ko, en, vi, ja, th) |
| `backend/app/data/rag_seed/` | RAG 시드 | 노동법 안내 JSON 데이터 (4 파일) |
| `.kiro/steering/` | AI 규칙 | 아키텍처·기술·제품·도메인·보안 불변식 |
| `.kiro/specs/` | 설계 스펙 | speech-to-text, multilingual-translation 설계서 |

## Test Packages

| Package | Type | Purpose | Test Count |
|---------|------|---------|-----------|
| `backend/tests/` | pytest | Backend API/서비스 단위 테스트 | 11 파일 |
| `worker/tests/` | pytest | Worker 규칙 엔진 + 통합 테스트 | 20 파일 |
| `eval/` | 평가 하네스 | OCR 정확도 회귀 측정 | 2 파일 + dataset |

## Total Count

| Category | Count |
|----------|------:|
| **Application** | 5 (backend, worker, static frontend, mobile-legacy, mobile-native) |
| **Infrastructure** | 5 (Terraform + 4 workflows) |
| **Shared** | 5 (prompts, locales, rag_seed, steering, specs) |
| **Test** | 3 (backend tests, worker tests, eval) |
| **Total Packages** | **18** |

## Implementation Completeness

| Component | 완성도 | 핵심 갭 |
|-----------|--------|---------|
| Backend API | 90% | Cognito 인증 연동 미완 (AUTH_MODE=demo) |
| Worker Consumer | 85% | 코드 완성, ECS 미기동 (desired=0) |
| Worker Transcription | 10% | handler 골격만, 실제 로직 미구현 |
| Static Frontend | 75% | 기능 동작, 모바일 UX/다국어 미진 |
| Next.js Frontend | 0% | README만 존재, 실제 코드 없음 |
| Terraform Infra | 95% | HTTPS/ACM 미적용 |
| CI/CD | 90% | Worker 실행 검증 미완 |
| RAG 챗봇 | 70% | Mock 모드에서 동작, Bedrock 연동 검증 필요 |
| GPS | 80% | 수집/판정 동작, E2E 분석 연결 미완 |
| Mobile Native | 75% | M1~M3 화면 완료, 백그라운드 GPS·인증 딥링크·출시빌드 미완 |
| PDF 생성 | 40% | report_builder.py 골격, WeasyPrint 렌더 미검증 |
| 커뮤니티 | 85% | 게시판 CRUD/번역/신고 완성, 실서비스 미검증 |
