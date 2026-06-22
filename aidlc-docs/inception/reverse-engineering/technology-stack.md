# Technology Stack

## Programming Languages

| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.11 | Backend API + Worker (FastAPI, boto3, SQLAlchemy) |
| JavaScript (Vanilla) | ES2020+ | Static Frontend SPA |
| HCL | Terraform 1.x | Infrastructure as Code |
| YAML | - | GitHub Actions CI/CD |

## Frameworks

| Framework | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.115.0 | REST API 서버 (비동기, OpenAPI 자동 생성) |
| SQLAlchemy | 2.0.35 | ORM, DB 세션 관리, 마이그레이션 기반 |
| Alembic | 1.13.3 | DB 스키마 마이그레이션 |
| Pydantic | 2.9.2 | 데이터 검증, 설정 관리, LLM 출력 스키마 |
| Jinja2 | 3.1.4 | PDF 렌더링용 HTML 템플릿 |
| WeasyPrint | 62.3 | HTML/CSS → PDF 변환 (다국어 폰트) |
| Capacitor | (package.json) | 모바일 앱 래퍼 (스트레치) |

## Infrastructure (AWS)

| Service | Purpose | Status |
|---------|---------|--------|
| ECS Fargate | Backend + Worker 컨테이너 실행 | ✅ Backend 실행 중 |
| ECR | Docker 이미지 저장소 (backend/worker) | ✅ |
| ALB | API 진입점 (HTTP) | ✅ (HTTPS 미적용) |
| RDS PostgreSQL | 핵심 데이터 저장 (Single-AZ, private subnet) | ✅ |
| PostGIS | GPS 공간 연산 확장 | ✅ |
| pgvector | RAG 임베딩 벡터 검색 | ✅ |
| S3 | 증거 파일 + 리포트 PDF 저장 (KMS-SSE) | ✅ |
| SQS + DLQ | 비동기 분석 작업 큐 | ✅ |
| Cognito | 사용자 인증 (User Pool + Google IdP) | ✅ (인프라), ⚠️ (앱 연동 미완) |
| Secrets Manager | DB 비밀번호, JWT secret 등 민감 정보 | ✅ |
| SSM Parameter Store | 비민감 설정값 (Cognito domain 등) | ✅ |
| Amazon Bedrock | Claude Sonnet 4.6 — OCR, 문장화, 요약, 챗봇 | ✅ (권한), ⚠️ (ECS 실호출 미검증) |
| Amazon Translate | 다국어 번역 | ✅ (구현) |
| Amazon Transcribe | 음성 전사 | ⚠️ (Provider 구현, handler 미연결) |
| CloudWatch | 로그 수집 + 경보 8개 | ✅ |
| SNS | 알림 이메일 전송 | ✅ |
| KMS | S3 버킷 암호화 키 | ✅ |
| VPC | 네트워크 격리 (public + private subnets) | ✅ |

## Build Tools

| Tool | Version | Purpose |
|------|---------|---------|
| pip | - | Python 패키지 관리 |
| Docker | - | 컨테이너 이미지 빌드 |
| docker-compose | - | 로컬 PostgreSQL 실행 |
| Terraform | 1.x | AWS 인프라 프로비저닝 |
| GitHub Actions | - | CI/CD (테스트, 빌드, 배포) |
| Alembic | 1.13.3 | DB 마이그레이션 관리 |

## Testing Tools

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | 8.3.3 | Python 단위/통합 테스트 |
| httpx | 0.27.2 | FastAPI TestClient (비동기 HTTP 테스트) |
| eval/harness.py | - | OCR 정확도 회귀 측정 커스텀 하네스 |
| eval/ocr_score.py | - | OCR 결과 점수 산출 |

## External APIs / SDKs

| API | SDK | Purpose |
|-----|-----|---------|
| AWS Bedrock | boto3 | Claude Sonnet 4.6 호출 (OCR, 요약, 챗봇) |
| Amazon Translate | boto3 | 다국어 번역 |
| Amazon Transcribe | boto3 | 음성 전사 |
| Upstage Document Parse | requests | 정형 문서 OCR |
| Parseur | requests | 대안 문서 파싱 |
| 카카오톡 스킬 API | urllib | 챗봇 연동 |
| Google OAuth | Cognito | 소셜 로그인 |
| 카카오 OAuth | requests | 소셜 로그인 |
| 네이버 OAuth | requests | 소셜 로그인 |

## 금지 스택 (tech.md 기준)

| 금지 | 이유 | 대안 |
|------|------|------|
| Kubernetes | 5주에 운영 불가 | ECS Fargate |
| Kafka | 트래픽 과잉 | SQS |
| NAT Gateway | 고정비 부담 | ECS public subnet |
| OpenAI | AWS 신뢰경계 외부 | Bedrock Claude |
| Textract | 한국어 미지원 | Claude Vision / Upstage |
| ReportLab | 다국어 합자 취약 | WeasyPrint |
| Step Functions | W1 부담 | 단일 워커 순차 실행 |
