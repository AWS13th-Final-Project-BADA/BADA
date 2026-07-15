# BADA MVP Requirements

## Intent Analysis

- **User Request**: BADA 프로젝트를 프로덕션 수준으로 완성하여 AWS에 MVP 배포
- **Request Type**: Enhancement (기존 코드베이스 완성 + 배포)
- **Scope**: System-wide (Backend, Worker, Frontend, Infrastructure 전체)
- **Complexity**: Complex (다수 컴포넌트 연동, 인증, AI 서비스, 프론트엔드 전환)
- **Target Date**: 2026-06-29 (다음 주 내)
- **Final Demo**: 2026-07-10

---

## Functional Requirements

### FR-01: 인증 시스템 완성
- **Priority**: P0 (배포 차단)
- Cognito + Google IdP 완전 연동 (인프라 완료, 백엔드 code 교환/JWT 검증 구현)
- 카카오 OAuth 소셜 로그인 완성 (현재 골격 존재)
- `AUTH_MODE=cognito` 전환
- 사용자 세션 관리 (JWT 만료, 로그아웃)

### FR-02: Worker 전체 파이프라인 활성화
- **Priority**: P0 (핵심 기능)
- SQS consumer → OCR → 규칙 분석 → 번역 → 타임라인 → 요약 전체 흐름 동작
- Worker ECS Service `desired_count=1` 전환
- Bedrock Claude 실제 호출 검증 (ECS Task Role 기반)
- analyze_case + transcribe handler 모두 동작

### FR-03: 음성 전사 (Speech-to-Text)
- **Priority**: P1
- Amazon Transcribe 연동 완성 (worker/handlers/transcription.py 구현)
- 음성 증거 업로드 → S3 → SQS → Worker → Transcribe → 텍스트 저장
- 한국어(ko-KR) 기본, 다국어 언어 코드 지원

### FR-04: PDF Evidence Pack 생성
- **Priority**: P1
- WeasyPrint로 제출용(ko) PDF 1종 완성
- 다국어 폰트 임베딩 (Noto Sans CJK, Khmer, Devanagari)
- 타임라인 + 차액/공제표 + GPS 요약 + 면책 고지 포함
- S3 Report Bucket 저장

### FR-05: 커뮤니티 게시판 배포
- **Priority**: P2
- 현재 구현된 게시판/댓글/번역/신고 기능 그대로 프로덕션 배포
- 콘텐츠 모더레이션(safety-check) 동작 확인

### FR-06: 카카오톡 봇 연동
- **Priority**: P2
- 카카오 스킬 서버 `/kakao/skill` 엔드포인트 프로덕션 연결
- 증거 업로드, GPS 핑, 분석 결과 조회, 계정 연동 기능

### FR-07: Next.js 프론트엔드
- **Priority**: P1
- Next.js (App Router) + Tailwind + next-intl로 새 프론트엔드 구축
- CloudFront + S3 또는 별도 ECS로 배포
- 화면: 로그인, 사건 생성, 증거 업로드, 결과(타임라인/분석/GPS), 커뮤니티, 챗봇
- 다국어: ko, vi, en 완성 / km, ne, id 골격

---

## Non-Functional Requirements

### NFR-01: HTTPS / TLS
- **Priority**: P0 (배포 차단)
- ACM 인증서 발급 + ALB HTTPS listener (443)
- HTTP → HTTPS 리다이렉트
- 커스텀 도메인 구매 예정 — 우선 ALB DNS로 HTTPS 적용, 도메인 준비되면 Route 53 연결

### NFR-02: 보안 (Security Baseline 전체 적용)
- **Priority**: P0
- SECURITY-01 ~ SECURITY-15 규칙 준수
- CORS 도메인 제한 (`allow_origins=["*"]` 제거)
- HTTP 보안 헤더 (CSP, HSTS, X-Frame-Options 등)
- Rate limiting (public endpoints)
- JWT secret을 Secrets Manager에서 주입
- 입력 검증 강화 (Pydantic + 길이/형식 제한)
- ALB access logging 활성화

### NFR-03: 복원력 (Resiliency Baseline 적용)
- **Priority**: P1
- Health check 기반 자동 복구 (ECS)
- SQS DLQ로 실패 메시지 격리
- Bedrock/Translate 호출 실패 시 graceful degradation
- RDS backup + restore 절차 정의
- CloudWatch Alarm 기반 알림 (이미 구축)

### NFR-04: Property-Based Testing (전체 적용)
- **Priority**: P1
- Hypothesis 프레임워크 도입 (Python)
- 규칙 엔진(wage, deductions, geofence, compare, legal, guardrails) PBT 추가
- round-trip, invariant, idempotency 속성 테스트
- CI에서 PBT 실행 + 시드 기록

### NFR-05: 성능
- **Priority**: P2
- 분석 응답 시간: 단일 사건 5분 이내 (OCR + 규칙 + 번역 + 요약)
- API 응답 시간: 일반 CRUD 500ms 이내
- PDF 생성: 30초 이내

### NFR-06: 비용
- **Priority**: P0
- 팀 전체 AWS 예산: 1,500달러 (2026-06-04 ~ 2026-07-10)
- Bedrock Claude 호출 비용 모니터링 (AWS Budgets)
- ECS Fargate 최소 사양 (Backend 1 task, Worker 1 task)
- RDS Single-AZ 유지

### NFR-07: 가용성
- 데모 기간(~7/10) 동안 95% 이상 가용
- 단일 AZ 장애 시 수동 복구 허용 (Multi-AZ는 Phase 2)

### NFR-08: 관측성
- CloudWatch Logs (Backend + Worker)
- CloudWatch Alarms 8개 (ALB, ECS, RDS, SQS)
- SNS 이메일 알림 동작
- CloudWatch MCP 읽기 전용 연결 완료

---

## Technical Decisions

| 결정 | 선택 | 근거 |
|------|------|------|
| 인증 | Cognito + 소셜(카카오/구글) | 인프라 이미 완성, 보안 기준 충족 |
| Worker | 전체 활성화 | 핵심 비즈니스 가치(OCR→분석→결과) |
| Frontend | Next.js 전환 | 모바일 UX, SSR, 다국어, 유지보수성 |
| HTTPS | ACM + ALB | 보안 필수, 도메인 추후 연결 |
| PDF | WeasyPrint MVP 포함 | 데모 핵심 산출물 |
| STT | Transcribe 포함 | 음성 증거 처리 요구 |
| PBT | Hypothesis 전체 적용 | 규칙 엔진 신뢰성 보장 |
| 보안 | Security Baseline 전체 | 민감 개인정보(급여, GPS) 보호 |
| 복원력 | Resiliency Baseline 적용 | 데모 안정성 |

---

## Scope Summary

### MVP 포함 (6/29까지)
- ✅ Cognito + 카카오/구글 인증
- ✅ Worker 전체 파이프라인 (OCR → 분석 → 번역 → 타임라인 → 요약)
- ✅ 음성 전사 (Amazon Transcribe)
- ✅ PDF Evidence Pack (제출용 ko)
- ✅ HTTPS (ACM + ALB)
- ✅ Next.js 프론트엔드
- ✅ 커뮤니티 게시판
- ✅ 카카오톡 봇
- ✅ 보안 강화 (CORS, 헤더, Rate limit, 입력 검증)
- ✅ PBT (Hypothesis)

### MVP 제외 (Phase 2)
- ❌ Multi-AZ / Auto Scaling
- ❌ 이해용 모국어 PDF (화면으로 대체)
- ❌ 16개국 언어 (vi + en + ko 우선)
- ❌ 네이티브 앱 백그라운드 GPS
- ❌ 진정서 자동 제출
- ❌ 노무사 매칭
- ❌ 주휴/야간수당 자동 판별

---

## Constraints

- AWS 예산: 1,500달러 총액
- 기간: ~2026-07-10 (데모 최종)
- 팀 규모: 소규모 팀 (OWNERSHIP.md 기준 7개 역할)
- 금지 스택: K8s, Kafka, NAT GW, OpenAI, Textract, ReportLab, Step Functions
- 네트워크: ALB/ECS public subnet, RDS private subnet, NAT Gateway 미사용
