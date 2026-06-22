# 컴포넌트 정의

## 시스템 컴포넌트 목록

### 1. Frontend (Next.js) — 신규
- **목적**: 사용자 인터페이스 (모바일 우선 반응형 웹)
- **배포**: ECS Fargate (SSR), `bada.kr` 도메인
- **책임**:
  - 페이지 렌더링 (SSR + CSR 하이브리드)
  - 다국어 UI (next-intl: ko, vi, en)
  - Cognito 인증 흐름 (로그인/로그아웃/토큰 관리)
  - Backend API 호출 (ALB `api.bada.kr` 직접)
  - PWA 지원 (Service Worker, 오프라인 기본 안내)
- **인터페이스**: HTTPS → ALB → Backend API

### 2. Backend API (FastAPI) — 기존 + 보안 강화
- **목적**: REST API 서버, 비즈니스 로직 오케스트레이션
- **배포**: ECS Fargate, `api.bada.kr` 도메인
- **책임**:
  - REST API 제공 (Cases, Evidences, Analysis, GPS, Chat, Community, Kakao)
  - Cognito JWKS 토큰 검증
  - 파일 업로드 → S3 저장
  - SQS 메시지 발행 (analyze_case, transcribe)
  - OCR 즉시 호출 (소규모 파일)
  - AI 챗봇 오케스트레이션
  - 보안 헤더, Rate limiting, CORS
- **인터페이스**: ALB(HTTPS) ← Frontend/카카오/모바일

### 3. Worker (SQS Consumer) — 기존 + 2단계 전환
- **목적**: 비동기 분석 파이프라인 실행
- **배포**: ECS Fargate, `desired_count=1`
- **책임**:
  - SQS 장기 폴링 + 메시지 디스패치
  - 사건 분석: OCR → 규칙엔진 → 번역 → 타임라인 → 요약 → DB 저장 (직접)
  - 음성 전사: S3 → Transcribe → 텍스트 저장
  - PDF Evidence Pack 생성 (WeasyPrint)
  - **DB 직접 접근** (2단계 전환, Backend 경유 제거)
- **인터페이스**: SQS ← Backend, RDS/S3/Bedrock/Translate/Transcribe 직접

### 4. Infrastructure (Terraform) — 기존 + HTTPS/Frontend 추가
- **목적**: AWS 리소스 프로비저닝
- **책임**:
  - VPC/서브넷/보안그룹
  - ECS Cluster (Backend + Worker + Frontend)
  - ALB (HTTPS, 도메인 라우팅)
  - ACM 인증서 (도메인 검증)
  - RDS PostgreSQL
  - S3 (Evidence + Report)
  - SQS + DLQ
  - Cognito
  - CloudWatch / SNS
  - Route 53 (도메인 준비 시)

### 5. CI/CD (GitHub Actions) — 기존 + Frontend 추가
- **목적**: 자동 빌드/테스트/배포
- **책임**:
  - Backend 자동배포 (develop push → ECR → ECS)
  - Worker 자동배포 (worker/** 변경 시)
  - Frontend 자동배포 (신규: frontend/** → ECR → ECS)
  - CI 테스트 (pytest + PBT + eval harness)
  - Backend 수동 롤백
