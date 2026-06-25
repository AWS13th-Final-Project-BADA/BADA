# BADA

외국인·취약 노동자가 흩어진 증거를 올리면, AI가 OCR·번역으로 사실관계를 구조화하여
**사건 타임라인 + 미지급 의심 금액 + 상담/신고 제출용 Evidence Pack(PDF)** 을 만들고,
다음 행동을 모국어로 안내하는 도구.

> ⚖️ BADA는 법률자문이 아니라 **상담 준비용 증거 정리 도구**입니다.
> 위법·체불 여부, 받을 금액을 확정하지 않습니다.

## 설계 원칙 (한 줄)

**계산·비교·정렬·판정은 규칙 기반 코드. 문장화·요약·OCR만 LLM.**
→ "AI가 금액을 잘못 계산하면?"에 "계산은 AI가 안 한다"고 답할 수 있다.

## 리포 구조

```
backend/        FastAPI API 서버
worker/         분석 워커 (rules = 규칙엔진, llm = OCR·문장화)
mobile-native/  React Native + Expo 모바일 앱 (주력 프론트엔드)
prompts/        LLM 프롬프트 템플릿
infra/          Terraform (AWS IaC)
monitoring/     Prometheus + Grafana 설정
eval/           평가셋 + 정확도 측정
docs/           프로젝트 문서 (README.md에 목차)
  architecture/   시스템 설계 (OCR, STT, 번역, GPS, Agent)
  infra/          인프라 설계/현황/로드맵
  operations/     운영/모니터링 가이드
  mobile/         모바일 E2E 테스트
  decisions/      의사결정 기록 (ADR)
  runbooks/       장애 대응 절차
  troubleshooting/ 트러블슈팅
```

## 빠른 시작 (로컬)

```bash
# 1) DB (postgres + postgis)
docker compose up -d

# 2) 백엔드
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# 3) 규칙 엔진 테스트 (LLM/AWS 없이 동작)
cd worker && pip install -r requirements.txt && pytest -q

# 4) 모바일 앱 (Expo)
cd mobile-native && npm install && npx expo start
```

## 아키텍처

### 현재 (As-Is)

```mermaid
flowchart TB
    %% ─── Client ───
    Mobile["📱 Mobile App\n(React Native + Expo)"]

    %% ─── Edge ───
    subgraph Edge["Edge / Ingress"]
        Cognito["Cognito\nGoogle IdP + PKCE"]
        ALB["ALB\nHTTPS · ACM · TLS 1.3"]
    end

    %% ─── Compute ───
    subgraph Compute["ECS Fargate Cluster"]
        Backend["Backend\nFastAPI :8000"]
        Worker["Worker\n분석 파이프라인"]
        Prom["Prometheus"]
        Graf["Grafana"]
    end

    %% ─── Data ───
    subgraph Data["데이터 계층 (Region Services)"]
        RDS[("RDS PostgreSQL 16\n+ PostGIS · Single-AZ")]
        S3["S3 Evidence / Report\nSSE-KMS"]
        SQS["SQS\n+ DLQ (redrive ×5)"]
    end

    %% ─── AI ───
    subgraph AI["AI / ML Services"]
        Bedrock["Bedrock\nClaude Sonnet 4"]
        Transcribe["Amazon Transcribe"]
        Translate["Amazon Translate"]
    end

    %% ─── Observability ───
    subgraph Obs["Observability"]
        CW["CloudWatch\nLogs · Alarms (14)"]
        SNS["SNS → Email"]
    end

    %% ─── Flows ───
    Mobile -->|HTTPS| ALB
    Mobile -->|OAuth PKCE| Cognito
    Cognito -->|Token| Backend
    ALB --> Backend

    Backend --> RDS
    Backend --> S3
    Backend -->|SendMessage| SQS

    SQS -->|ReceiveMessage| Worker
    Worker --> Bedrock
    Worker --> Transcribe
    Worker --> Translate
    Worker --> RDS
    Worker --> S3

    Backend -.->|logs| CW
    Worker -.->|logs| CW
    Prom --> Graf
    Graf -.->|alert| SNS
    CW -.->|alarm| SNS
```

### 목표 (To-Be)

```mermaid
flowchart TB
    %% ─── Client ───
    Mobile["📱 Mobile App\n(React Native + Expo)"]

    %% ─── Edge ───
    subgraph Edge["Edge / Security"]
        WAF["AWS WAF\nOWASP Managed Rules"]
        ALB["ALB (Public Subnet)\nHTTPS · ACM"]
    end

    %% ─── Network ───
    subgraph Network["Network"]
        NAT["NAT Gateway"]
        VPCE["VPC Endpoints\nS3 · SQS · ECR"]
    end

    %% ─── Compute (Private Subnet) ───
    subgraph Private["Private Subnet"]
        subgraph ECS["ECS Fargate + Auto Scaling"]
            Backend["Backend ×1~3\nCPU 70% scaling"]
            Worker["Worker ×1~3 (Spot)\nSQS backlog scaling"]
            Prom["Prometheus"]
            Graf["Grafana"]
        end
        RDS[("RDS PostgreSQL 16\nMulti-AZ · Encrypted")]
    end

    %% ─── Data (Region Services) ───
    subgraph Data["데이터 계층"]
        S3["S3 Evidence / Report\nSSE-KMS · Lifecycle"]
        SQS["SQS + DLQ"]
    end

    %% ─── AI ───
    subgraph AI["AI / ML Services"]
        Bedrock["Bedrock\nClaude Sonnet 4"]
        Transcribe["Amazon Transcribe"]
        Translate["Amazon Translate"]
    end

    %% ─── Security & Observability ───
    subgraph SecObs["Security & Observability"]
        XRay["X-Ray\n분산 추적"]
        Guard["GuardDuty"]
        SecHub["Security Hub"]
        CW["CloudWatch"]
        SNS["SNS → Email"]
    end

    %% ─── Auth ───
    Cognito["Cognito\nGoogle IdP"]

    %% ─── Flows ───
    Mobile -->|HTTPS| WAF
    WAF --> ALB
    ALB --> Backend
    Mobile -->|OAuth PKCE| Cognito
    Cognito -->|Token| Backend

    Backend --> RDS
    Backend -->|VPC Endpoint| S3
    Backend -->|VPC Endpoint| SQS

    SQS --> Worker
    Worker --> Bedrock
    Worker --> Transcribe
    Worker --> Translate
    Worker --> RDS
    Worker -->|VPC Endpoint| S3

    Private -->|outbound| NAT
    Private -.-> VPCE

    Backend -.-> XRay
    Worker -.-> XRay
    Backend -.->|logs| CW
    Worker -.->|logs| CW
    CW -.->|alarm| SNS
    Graf -.->|alert| SNS
    Guard --> SecHub
```

> 상세 설계: `docs/infra/production-roadmap.md` · 의사결정: `docs/decisions/decision-record-20260625.md`

## 스택

| 카테고리 | 서비스 |
|----------|--------|
| **컴퓨트** | ECS Fargate (ARM64) · ECR · ALB (HTTPS/ACM/TLS1.3) |
| **데이터** | RDS PostgreSQL + PostGIS · S3 (SSE-KMS) · SQS + DLQ |
| **인증** | Cognito (Hosted UI + PKCE + Google IdP) |
| **AI** | Bedrock Claude Sonnet 4 · Amazon Translate · Amazon Transcribe |
| **관측성** | CloudWatch Logs/Alarms · Prometheus · Grafana · SNS Alert |
| **보안** | Secrets Manager · SSM Parameter Store · WAF (예정) |
| **PDF** | WeasyPrint (다국어 폰트 임베딩) |
| **모바일** | React Native · Expo · EAS Build |
| **IaC** | Terraform · GitHub Actions OIDC |

**금지 스택**: K8s, Kafka, OpenAI, Textract, ReportLab — 사유는 `.kiro/steering/` 참조.

## 배포 현황

| 서비스 | URL | 상태 |
|--------|-----|------|
| Backend API | `https://api.badasoft.com` | ✅ |
| Grafana | `https://monitor.badasoft.com` | ✅ |
| 모바일 앱 | EAS Preview APK | 🔄 구현 중 |

## 인프라 운영 기준

- 프로젝트 운영 기간: `2026-06-04` ~ `2026-07-10`
- 팀 전체 AWS 총 예산: `1,500달러`
- 비용 통제: `RDS Single-AZ`, `Fargate 최소 사양`, `로그 보존기간 단축`
- 상세: `docs/infra/implementation-status.md`

## 문서

`docs/README.md` 참조. 주요 문서:

- [인프라 현황](docs/infra/implementation-status.md)
- [프로덕션 로드맵](docs/infra/production-roadmap.md)
- [의사결정 기록](docs/decisions/decision-record-20260625.md)
- [장애 대응 런북](docs/runbooks/)
- [팀 태스크 배분](aidlc-docs/team-task-distribution.md)

## CI/CD

- **CI**: pytest + coverage + bandit(SAST) + ruff(lint) — PR마다 자동 실행
- **Backend CD**: `develop` push → ECR → ECS 배포 → health check
- **Worker CD**: 동일 구조
- **모바일**: EAS Build (구현 예정)

## 테스트

```bash
# 전체 테스트 (215 tests)
cd backend && pytest -q
cd worker && pytest -q

# 커버리지 포함
pip install -r dev-requirements.txt
cd worker && pytest --cov=. --cov-report=term-missing
cd backend && pytest --cov=app --cov-report=term-missing
```
