# BADA 인프라 구현 현황

> 팀 공용 AWS 계정에 현재 구현된 BADA 인프라 상태를 한눈에 확인하기 위한 문서다.
> 실행 방법이나 상세 의사결정이 아니라, “무엇이 구축되어 있고 현재 어떤 상태인지”만 기록한다.

## 1. 전체 요약

| 항목 | 현재 상태 |
| --- | --- |
| AWS Region | `ap-northeast-2` |
| IaC | Terraform |
| 배포 대상 | ECS Fargate |
| 기준 브랜치 | `develop` |
| Backend 상태 | ECS Service 실행 중 |
| Frontend 상태 | Next.js ECS Service 실행 중, `https://badasoft.com` 연결 완료 |
| Worker 상태 | SQS consumer 구현 전으로 미실행, runtime 인프라 적용 완료 |
| DB | RDS PostgreSQL, private subnet |
| 파일 저장소 | S3 Evidence / Report Bucket |
| 비밀값 관리 | Secrets Manager |
| 설정값 관리 | SSM Parameter Store |
| 인증 인프라 | Cognito Hosted UI / Authorization Code Grant / Google IdP 적용 완료 |
| HTTPS/도메인 | `badasoft.com` ACM 인증서(ISSUED), ALB 443 리스너(TLS1.3), HTTP→HTTPS 301, Route 53 적용 완료 |
| Bedrock 모델 접근 | Anthropic FTU 제출 및 Claude Sonnet 4.6 Playground 호출 완료 |
| 팀원 모델 테스트 | 팀원 IAM 호출 권한 검증 완료, 모델 액세스는 자동 활성화(Model access 페이지 폐지)·IAM/SCP 통제 / `BEDROCK_MODEL_ID` 전환 |
| 배포 자동화 | Backend/Worker/Frontend GitHub Actions OIDC 배포 workflow 및 AWS 권한 반영 |
| 롤백 | GitHub Actions 수동 롤백 workflow |
| 모니터링 | Prometheus + Grafana ECS 배포, `monitor.badasoft.com`, Backend target UP, CloudWatch datasource, Logs / Alarms / SNS / CloudWatch MCP 연결 완료 |
| Well-Architected | Workload 생성 및 초기 milestone 저장 완료 |

## 2. 현재 실행 상태

| 구분 | 상태 |
| --- | --- |
| Backend ECS Service | `desired=1`, `running=1` |
| Frontend ECS Service | `desired=1`, `running=1` |
| Worker ECS Service | `desired=0`, `running=0` |
| Prometheus ECS Service | `desired=1`, `running=1`, Backend/Prometheus target UP |
| Grafana ECS Service | `desired=1`, `running=1`, Target Group healthy |
| Grafana URL | `https://monitor.badasoft.com`, `/api/health` 200 |
| Frontend Task Definition | `bada-dev-frontend:1` |
| Frontend Target Group | `healthy`, port `3000`, health path `/api/health` |
| Frontend URL | `https://badasoft.com` → `/ko`, `/api/health` 200 |
| Backend Task Definition | `bada-dev-backend:20` |
| Worker Task Definition | `bada-dev-worker:7` |
| Target Group | `healthy` |
| ALB `/health` | `200 {"status":"ok"}` |
| ALB `/version` | `200 {"name":"BADA","version":"0.1.0","auth_mode":"demo","storage_mode":"s3"}` |

## 3. 아키텍처 흐름

```text
Users
  -> ALB
      -> badasoft.com -> ECS Fargate Frontend
      -> api.badasoft.com -> ECS Fargate Backend
  -> RDS PostgreSQL / S3 / SQS / Cognito / Secrets Manager / SSM / CloudWatch

SQS
  -> ECS Fargate Worker
  -> AI / OCR / Translation
  -> RDS PostgreSQL / S3
```

현재 Worker는 인프라만 준비되어 있으며, 장기 실행 SQS consumer 구현 전까지 실행하지 않는다.

## 4. 리소스 구현 현황

### Network

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| VPC | 완료 | BADA dev 인프라 기본 네트워크 |
| Public Subnet 2개 | 완료 | ALB / ECS 배치 |
| Private Subnet 2개 | 완료 | RDS 배치 |
| Internet Gateway | 완료 | Public subnet 외부 통신 |
| Route Table / Association | 완료 | Public / Private routing 분리 |
| NAT Gateway | 미사용 | 비용 절감을 위해 MVP 단계 제외 |

### Compute / Container

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| ECS Cluster | 완료 | Backend / Worker 공용 |
| Backend Task Definition | 완료 | GitHub Actions 배포 기준 최신 revision 사용 |
| Frontend Task Definition | 완료 | ARM64, port 3000, Next.js standalone |
| Worker Task Definition | 완료 | `DATABASE_URL` Secret 주입 및 Service `:4` 연결 완료 |
| Backend ECS Service | 실행 중 | `desired_count=1` |
| Frontend ECS Service | 실행 중 | `desired_count=1`, Target healthy |
| Worker ECS Service | 대기 | `desired_count=0` |
| Backend ECR Repository | 완료 | Backend image 저장 |
| Frontend ECR Repository | 완료 | Frontend ARM64 image 저장 |
| Worker ECR Repository | 완료 | Worker image 저장 |
| ALB | 완료 | Host 기반 Frontend/Backend 진입점 |
| Target Group | 완료 | Backend `/health`, Frontend `/api/health` 연결 |

### Data / Storage / Queue

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| RDS PostgreSQL | 완료 | Single-AZ, private subnet |
| RDS Deletion Protection | 완료 | 실수 삭제 방지 |
| RDS Automated Backup | 완료 | 7일 보존 |
| RDS Final Snapshot | 완료 | 삭제 시 최종 스냅샷 생성 |
| PostGIS Extension | 완료 | GPS 위치 데이터 확장 대비 |
| S3 Evidence Bucket | 완료 | 증거 파일 저장 |
| S3 Report Bucket | 완료 | 생성 리포트 저장 |
| S3 SSE-KMS | 완료 | 버킷 암호화 |
| SQS Analysis Queue | 완료 | Visibility Timeout 15분 / Long Polling 20초 적용 |
| SQS DLQ | 완료 | 실패 메시지 격리 |

### Auth / Config / Secret

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| Cognito User Pool | 완료 | `ap-northeast-2_5K39SlMFg` |
| Cognito App Client | 완료 | Authorization Code Grant, callback/logout URL, `openid email profile`, `COGNITO`/`Google` provider 적용 |
| Cognito Hosted UI Domain | 완료 | `https://bada-dev-165749212250.auth.ap-northeast-2.amazoncognito.com/` |
| Cognito Google IdP | 완료 | Terraform apply 및 Google OAuth `302` redirect 검증 |
| Secrets Manager | 완료 | DB 접속 정보와 앱 secret |
| SSM Parameter Store | 완료 | Cognito domain/redirect/logout/scopes를 포함한 비민감 설정 |
| IAM User / Role | 완료 | 팀원 접근, GitHub Actions 배포 역할, CloudWatch MCP 읽기 전용 역할 |

Cognito 연동값:

```text
COGNITO_USER_POOL_ID=ap-northeast-2_5K39SlMFg
COGNITO_CLIENT_ID=2n7fd1lbtifh3d3269i400es1f
COGNITO_DOMAIN=https://bada-dev-165749212250.auth.ap-northeast-2.amazoncognito.com/
COGNITO_REDIRECT_URI=http://localhost:8000/auth/cognito/callback
COGNITO_LOGOUT_URI=http://localhost:8000/
COGNITO_SCOPES=openid email profile
```

- 기존 App Client를 인플레이스 수정해 Client ID를 유지했다.
- Google IdP는 `email`, `email_verified`, `name`, `username(sub)` 속성 매핑을 사용한다.
- Google Client Secret은 비추적 `infra/terraform.tfvars`와 암호화된 Terraform remote state에서만 관리한다.
- Hosted UI에서 Google OAuth 진입까지 검증했으며 callback code 교환과 JWT 검증은 인증 담당 범위다.
- 인프라 설정은 완료됐지만 Backend의 `AUTH_MODE`는 아직 `demo`다. 인증 담당자가 Cognito callback/code 교환과 JWT 검증을 구현한 뒤 `AUTH_MODE=cognito`로 전환해야 한다.

### AI / Bedrock

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| Anthropic First Time Use | 완료 | 팀 AWS 계정에서 use case details 제출 |
| 대상 모델 | 완료 | `global.anthropic.claude-sonnet-4-6` |
| Playground 호출 | 완료 | 서울 리전에서 정상 응답 확인 |
| ECS Task Role 권한 | 완료 | `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` |
| 애플리케이션 호출 | 검증 대기 | Backend/Worker의 실제 Task Role 호출과 CloudWatch Logs 확인 필요 |

- Anthropic FTU는 IAM 권한과 별개인 AWS 계정 단위 최초 1회 등록 절차다.
- FTU 제출은 콘솔 또는 AWS API로 가능하지만 현재 Terraform 리소스로 관리하지 않는다.
- Playground 성공으로 계정의 Claude 접근은 확인했으며, 서비스 연동 완료 여부는 ECS 런타임 호출로 별도 검증한다.

#### 팀원 모델 자유 테스트 접근

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| 팀원 IAM 호출 권한 | 완료 | `bada-hsw`, `bada-kjh`, `bada-ldk`, `bada-sjw` 모두 `bedrock:InvokeModel` 등 `allowed` (PowerUserAccess 상속) |
| 모델 액세스 방식 | 자동 | Bedrock `Model access` 페이지 폐지, 서버리스 모델은 첫 호출 시 자동 활성화 (통제는 IAM/SCP) |
| 모델 전환 방식 | 완료 | 앱이 `BEDROCK_MODEL_ID` 환경변수로 모델 지정 (기본값 `global.anthropic.claude-sonnet-4-6`) |
| 비용 안전망 | 권장 | AWS Budgets의 Bedrock 비용 알림으로 고가 모델 반복 호출 통제 |

- OCR/음성인식 담당자가 후보를 미리 정하지 않고 여러 모델을 바꿔가며 테스트할 수 있도록 구성한다.
- Bedrock 호출은 `IAM 권한`과 `모델 액세스` 두 층을 통과해야 하며, IAM은 이미 충족되어 있다.
- Bedrock `Model access` 수동 활성화 페이지는 폐지됐고, 서버리스 파운데이션 모델은 계정에서 처음 호출되는 순간 자동 활성화된다(Anthropic FTU 1회 완료, Marketplace 모델만 최초 1회 invoke 필요).
- 모델 접근 통제는 콘솔 토글이 아니라 IAM 정책/SCP로 하며, 넓게 열려면 현재 PowerUserAccess로 충분하다.
- 팀원은 로컬에서 `BEDROCK_MODEL_ID`만 바꿔 모델을 교체하며, `global.`/`apac.` cross-region profile보다 리전 내 on-demand 모델 ID 사용을 권장한다.

### Observability / Cost

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| CloudWatch Log Group | 완료 | Backend / Worker 로그 |
| CloudWatch Alarm | 완료 | ALB, ECS, RDS, SQS 핵심 지표 8개 |
| SNS Alarm Topic | 완료 | Alarm 8개 action 연결 완료 |
| SNS Email Subscription | 완료 | `badajoa0710@gmail.com`, 테스트 메시지 및 Alarm/OK 경로 검증 |
| CloudWatch MCP | 완료 | 전용 AssumeRole 최소권한, 서버 1.28.0, Backend/Worker Log Group 및 활성 Alarm 조회 검증 |
| AWS Budgets | 완료 | 팀 예산 추적 |
| Well-Architected Tool | 초기 등록 완료 | Workload / Milestone 생성 |

## 5. 배포 자동화 현황

### Backend 자동배포

```text
develop push
  -> GitHub Actions OIDC Role Assume
  -> Backend Docker image build
  -> ECR push
  -> ECS Task Definition 새 revision 등록
  -> ECS Service update
  -> ALB /health 검증
```

| 항목 | 상태 |
| --- | --- |
| Workflow | `.github/workflows/deploy-dev.yml` |
| Trigger | `develop` push |
| 인증 방식 | GitHub Actions OIDC |
| 배포 대상 | Backend ECS Service |
| 배포 후 검증 | ALB `/health` |

### Worker 자동배포

```text
develop push
  -> GitHub Actions OIDC Role Assume
  -> Worker Docker image build
  -> ECR push
  -> ECS Task Definition 새 revision 등록
  -> ECS Service update
  -> ECS Service 상태 출력
```

| 항목 | 상태 |
| --- | --- |
| Workflow | `.github/workflows/deploy-dev-worker.yml` |
| Trigger | `worker/**` 변경이 포함된 `develop` push 또는 수동 실행 |
| 인증 방식 | GitHub Actions OIDC |
| 배포 대상 | Worker ECS Service |
| 현재 실행 상태 | `desired_count=0` 유지 |
| AWS 권한 반영 | 완료. Deploy Role이 Backend / Worker ECR push 가능 |
| 실행 검증 | 완료. image / Task Definition revision 갱신과 Service 상태 출력 확인 |

Worker는 아직 SQS long-running consumer가 구현되지 않았으므로, 배포 workflow는 이미지와 Task Definition revision을 갱신하는 용도로만 사용한다. Worker consumer가 완성되면 Terraform에서 `worker_desired_count`를 올려 실제 실행 상태로 전환한다.

Worker runtime 사전 준비:

```text
SQS Visibility Timeout : 30초 -> 900초
SQS Receive Wait Time   : 0초 -> 20초
Worker DATABASE_URL     : Secrets Manager database_url 주입
terraform validate      : Success
terraform apply         : Success
terraform plan          : No changes
Worker Task Definition  : bada-dev-worker:4
Worker Service          : desired=0, running=0 유지
```

검증 기록:

```text
terraform apply : success
changed         : 1 IAM role policy
terraform plan  : No changes
Worker service  : desired=0, running=0
```

주의: 현재 GitHub 기본 브랜치가 `main`이므로, `develop`에만 존재하는 신규 workflow는 GitHub Actions 수동 실행 목록에 바로 노출되지 않을 수 있다. Worker workflow 실제 실행 검증은 `worker/**` 변경이 `develop`에 push될 때 자동 실행되거나, workflow가 default branch에 반영된 뒤 수동 실행으로 진행한다.

### Frontend 자동배포

```text
frontend/** develop push
  -> GitHub Actions OIDC Role Assume
  -> ARM64 Next.js image build
  -> Frontend ECR push
  -> ECS Task Definition 새 revision 등록
  -> ECS Service update
  -> https://badasoft.com/api/health 검증
```

| 항목 | 상태 |
| --- | --- |
| Workflow | `.github/workflows/deploy-dev-frontend.yml` |
| Trigger | `frontend/**` 변경이 포함된 `develop` push 또는 수동 실행 |
| 인증 방식 | GitHub Actions OIDC |
| 배포 대상 | `bada-dev-frontend` ECS Service |
| 이미지 아키텍처 | `linux/arm64` |
| 실행 상태 | `desired=1`, `running=1`, Target healthy |
| 배포 후 검증 | `https://badasoft.com/api/health` 200 |

최초 배포는 ECR/Task Definition/Service를 `desired=0`으로 먼저 생성하고, 이미지 push 성공 후 `desired=1`로 전환하는 2단계로 수행했다. 빈 ECR 상태에서 Service가 반복 실패하거나 빈 Target Group으로 트래픽이 전달되는 것을 방지하기 위한 순서다.

### Backend 수동 롤백

```text
workflow_dispatch
  -> rollback 대상 Task Definition 입력
  -> ECS Service update
  -> services-stable 대기
  -> ALB /health 검증
```

| 항목 | 상태 |
| --- | --- |
| Workflow | `.github/workflows/rollback-dev-backend.yml` |
| 실행 방식 | 수동 실행 |
| 입력값 | 롤백할 Backend Task Definition |
| 제한사항 | DB migration, 데이터 변경, Secrets 변경은 별도 복구 필요 |

## 6. 현재 미구현 / 대기 항목

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| Worker SQS long-running consumer | 미구현 | 구현 후 Worker Service 기동 필요 |
| Worker runtime 인프라 적용 | 완료 | SQS 설정, DB Secret, Service `:4` 연결 검증 |
| Worker 자동배포 실행 검증 | 완료 | consumer 구현 후 실제 메시지 처리 검증은 별도 진행 |
| Amazon Transcribe 독립 모드 | 완료 | Backend `:20`, Worker `:7`에 `TRANSCRIBE_MODE=aws` 배포 및 ALB health 검증 |
| Anthropic Claude 계정 접근 | 완료 | FTU 제출 및 Global Claude Sonnet 4.6 Playground 호출 검증 |
| ECS Bedrock 실제 호출 | 검증 대기 | Task Role 기반 호출과 CloudWatch Logs 확인 필요 |
| Cognito Hosted UI/OAuth 인프라 | 완료 | Hosted UI, Authorization Code Grant, callback/logout URL 적용 |
| Cognito Google IdP | 완료 | PR #39 코드 반영 후 Terraform apply, App Client provider와 Google redirect 검증 |
| Google IdP Terraform drift | 완료 | PR #45 merge, AWS 자동 보정값 명시 및 최종 plan `No changes` 검증 |
| Cognito 애플리케이션 로그인 연동 | 개발 대기 | callback/code 교환, JWT 검증, `AUTH_MODE=cognito` 전환 필요 |
| Well-Architected 1차 답변 | 완료 | 57개 질문 답변 및 milestone #2 저장 |
| SNS 기반 알림 전송 | 완료 | 구독 확인, 테스트 메시지, Alarm → SNS 및 OK 복구 알림 경로 검증 |
| CloudWatch MCP | 완료 | `bada-mcp-readonly` 프로필로 Log Group/Alarm 실제 조회 및 S3 접근 거부 확인 |
| Frontend ECS 배포 | 완료 | Next.js 15.5.19, ECR/Task/Service/ALB host routing, `/api/health` 200 |

## 7. Well-Architected Tool 현황

| 항목 | 값 |
| --- | --- |
| Workload Name | `BADA Dev Infrastructure` |
| Workload ID | `95748e8dbd2cc80821d6429d20a9ef03` |
| Environment | `PREPRODUCTION` |
| Region | `ap-northeast-2` |
| Lens | `AWS Well-Architected Framework` |
| Initial Milestone | `2026-06-17 initial workload baseline` |
| First Review Milestone | `2026-06-17 first review answers` |
| Milestone Number | `1`, `2` |
| 현재 답변 상태 | 57개 질문 답변 완료 |

1차 리뷰 결과:

| Risk | 개수 |
| --- | ---: |
| High | 30 |
| Medium | 24 |
| None | 3 |
| Unanswered | 0 |

Pillar별 리스크:

| Pillar | High | Medium | None |
| --- | ---: | ---: | ---: |
| Operational Excellence | 7 | 4 | 0 |
| Security | 7 | 3 | 1 |
| Reliability | 8 | 5 | 0 |
| Performance Efficiency | 2 | 3 | 0 |
| Cost Optimization | 6 | 3 | 2 |
| Sustainability | 0 | 6 | 0 |

현재 High Risk는 대부분 MVP/dev 환경에서 일정과 비용을 우선해 의도적으로 미뤄둔 항목이다. 따라서 즉시 모든 리스크를 제거하기보다, 멘토링과 기능 통합에 필요한 항목부터 개선한다.

우선 개선 항목:

| 우선순위 | 개선 항목 | 관련 Pillar | 상태 |
| --- | --- | --- | --- |
| P0 | ALB HTTPS/ACM 적용 및 HTTP -> HTTPS redirect | Security | 완료 (`badasoft.com`, ACM ISSUED, 443 리스너, 301 리다이렉트, HTTPS /health 200) |
| P0 | CloudWatch Alarm SNS 이메일 수신 검증 | Operational Excellence / Reliability | 완료 |
| P0 | Worker SQS consumer 구현 후 Worker Service 기동 검증 | Reliability / Cost | 개발 대기 |
| P1 | RTO/RPO와 RDS restore rehearsal 절차 정의 | Reliability | 대기 |
| P1 | ECR image scan, dependency scan, CI 보안 검증 강화 | Security | 대기 |
| P1 | ECS Backend/Worker Auto Scaling과 부하 테스트 기준 수립 | Performance / Reliability | 대기 |
| P2 | Cost allocation tag, Cost Explorer/CUR 기반 비용 분석 강화 | Cost Optimization | 대기 |
| P2 | S3 lifecycle/retention 정책과 데이터 분류 기준 구체화 | Security / Sustainability | 대기 |

## 8. 참고 문서

| 문서 | 목적 |
| --- | --- |
| `infra/README.md` | Terraform 실행 방법과 인프라 코드 구조 |
| `docs/OWNERSHIP.md` | 파트별 담당 영역 |
| `.github/workflows/deploy-dev.yml` | Backend 자동배포 workflow |
| `.github/workflows/deploy-dev-worker.yml` | Worker 자동배포 workflow |
| `.github/workflows/deploy-dev-frontend.yml` | Frontend 자동배포 workflow |
| `.github/workflows/rollback-dev-backend.yml` | Backend 수동 롤백 workflow |
