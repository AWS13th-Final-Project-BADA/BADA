# AI-DLC State Tracking

## Project Information
- **Project Type**: Brownfield
- **Start Date**: 2026-06-19T17:26:13+09:00
- **Current Stage**: POST-MVP — 프로덕션 고도화 (인프라 고도화 #4/#11/#13/#15/#16 반영 2026-07-02; #5/#12/#18 보류)

## Workspace State
- **Existing Code**: Yes
- **Programming Languages**: Python (FastAPI backend, worker), JavaScript (static frontend), Terraform (IaC)
- **Build System**: pip (requirements.txt), Docker, Terraform
- **Project Structure**: Monolith (Backend API + Worker + Frontend static)
- **Workspace Root**: C:\AIDLC\BADA
- **Reverse Engineering Needed**: Yes (no existing aidlc-docs artifacts)

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis |
| Resiliency Baseline | Yes | Requirements Analysis |
| Property-Based Testing | Yes (Full) | Requirements Analysis |

## Stage Progress
- [x] INCEPTION - Workspace Detection
- [x] INCEPTION - Reverse Engineering (2026-06-19T17:28:46+09:00)
- [x] INCEPTION - Requirements Analysis (2026-06-22T09:31:57+09:00)
- [x] INCEPTION - User Stories — SKIP (기존 문서에 페르소나/흐름 정의됨)
- [x] INCEPTION - Workflow Planning (2026-06-22T09:39:41+09:00)
- [x] INCEPTION - Application Design — EXECUTE (2026-06-22T10:06:18+09:00)
- [x] INCEPTION - Units Generation — EXECUTE (2026-06-22T10:10:15+09:00)
- [x] CONSTRUCTION - Functional Design (per-unit, 6유닛 완료)
- [x] CONSTRUCTION - NFR Requirements (per-unit, 유닛 1 실행)
- [x] CONSTRUCTION - NFR Design (per-unit, 유닛 1 실행)
- [x] CONSTRUCTION - Infrastructure Design (per-unit, 유닛 1 실행)
- [x] CONSTRUCTION - Code Generation (per-unit, 6유닛 완료 2026-06-22T11:24:03+09:00)
- [x] CONSTRUCTION - Build and Test (2026-06-22T11:42:26+09:00)
- [x] POST-MVP - 모니터링 구축 (Prometheus+Grafana+Alert, 2026-06-22~25)
- [x] POST-MVP - 모바일 앱 (React Native+Expo, M1~M3 완료, 2026-06-25)
- [ ] POST-MVP - 프로덕션 고도화 (18건 의사결정 확정, 실행 중)
  - [x] #17 CI 강화 (ruff + bandit + pytest-cov) — 692034b
  - [x] 관측성 강화 (비즈니스 메트릭 + SLI/SLO + Alert 계층화) — 252d7e4
  - [x] docs/ 정리 (중복 제거 + 7폴더 분류) — 98543e6
  - [x] README.md 갱신 + 아키텍처 다이어그램 — e03263e
  - [x] 카오스 엔지니어링 시나리오 문서 — 81d2720
  - [x] 웹 프론트엔드 제거 + CD 정리 — bb58341
  - [x] #3 행 수준 인가 (verify_case_owner + Cases/Evidences API)
  - [x] #10 X-Ray SDK 통합 (Backend + Worker 수동 세그먼트, Service Map 확인 완료)
  - [x] #14 구조화 로깅 (python-json-logger + RequestIdMiddleware)
  - [x] OCR entities 근본 수정 (Dockerfile prompts/ 포함 + 1-pass 복귀)
  - [x] OCR 병렬 처리 (max_workers=50, 12건 240초→25초)
  - [x] 분석 시점 OCR 실행 (업로드 시 즉시 OCR 제거, 비용 절약)
  - [x] STT → entities 구조화 파이프라인 완성
  - [x] Worker CPU 상향 (256→1024, PDF 50초→15초)
  - [x] Container Insights 활성화
  - [x] Worker Prometheus 비즈니스 메트릭 추가
  - [x] 일괄 업로드 UX 변경 (파일 모아두기 → 업로드 실행)
  - [x] 분석 결과 다국어 지원 (DB 한국어 저장 + 조회 시 Amazon Translate 실시간 번역)
  - [x] 분석 결과 화면 i18n 하드코딩 제거
  - [x] PDF 항상 한국어 고정 (제출용 원본)
  - [x] FE 타임아웃 5분으로 상향
  - [x] Backend 실시간 번역 서비스 (translation.py) 추가
  - [x] #16 Terraform Plan in PR (terraform-plan.yml + 읽기전용 plan-role, 2026-07-02 확인)
  - [x] #4 Auto Scaling (Backend CPU 70% + Worker SQS backlog-per-task Target Tracking, min=1/max=3, `ignore_changes=[desired_count]` 안전판) — PR #203
  - [x] #13 Task Role 분리 (Backend/Worker 서비스별 최소권한 Role: producer vs consumer) — PR #205
  - [x] #15 Worker Fargate Spot (`FARGATE_SPOT` capacity provider, On-Demand base 토글, Backend는 On-Demand 유지) — PR #206
  - [x] #11 GuardDuty/Security Hub (본체 + `security_monitoring_enabled` 종료 토글 + PR 플랜 X-Ray drift 오탐 제거) — PR #207
  - [x] #1 소셜 OAuth 직접 구현 (구글/카카오/네이버 `/auth/{provider}/login·callback` + `bada://` 딥링크 토큰, `AUTH_MODE=oauth`, Cognito 미사용 협의)
  - [x] #19 모바일 로그인 E2E (앱 `WebBrowser.openAuthSessionAsync` → 딥링크 토큰 수신, 로그인 화면 3종 provider 코드 완비)
  - [x] #20 APK 배포 파이프라인 (`build-mobile.yml` EAS Build + `eas.json` preview/production, **수동 `workflow_dispatch` 전용**)
  - [x] Grafana Infrastructure 대시보드 수정 (ECS/ContainerInsights 적용 완료)
  - [x] Prometheus Worker 타겟 추가 (9090 포트 + Cloud Map 적용 완료)
  - [~] Phase 2~4 인프라 고도화 — #4/#11/#13/#15 완료(2026-07-02, TF 분리 없이 적용). #5(TF 분리)/#12(Private Subnet+NAT)/#18(VPC Endpoint)은 종료 기간·비용 대비 보류

## Post-MVP 의사결정 (2026-06-25 확정)
- 상세: `docs/decision-record-20260625.md`
- 웹 프론트엔드 제거 → mobile-native 전환 (deploy-dev-frontend.yml 삭제, frontend_enabled=false 예정)
- 즉시 실행: 19(모바일 로그인 E2E), 20(APK 배포), 3(행 수준 인가), 6(모델 비교), 10(X-Ray), 14(구조화 로깅), 16(TF Plan PR), 17(CI 강화)
- TF 분리 후 후보: 2·7·8(완료), **4·11·13·15(완료 — 2026-07-02, TF 분리 없이 적용)**, 5·12·18(보류 — 종료 기간·비용 대비 위험 초과)
- 최종 검증: 9(k6 부하 테스트) — 담당 진행 (Auto Scaling 머지로 발동 가능)
