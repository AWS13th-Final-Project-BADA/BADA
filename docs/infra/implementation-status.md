# BADA 인프라 구현 현황

> 팀 공용 AWS 계정에 현재 구현된 BADA 인프라 상태를 한눈에 확인하기 위한 문서다.
> 실행 방법이나 상세 의사결정이 아니라, "무엇이 구축되어 있고 현재 어떤 상태인지"만 기록한다.

> ⏱️ 일정: **구현 완성 마감 `2026-07-03 (금)`**, **인프라·서비스 유지 종료 `2026-07-10 (금)`**.
> 7/10 이후 비용 리소스 종료 예정.
>
> 📅 기준일(last-updated): **2026-07-03** — 3-tier 네트워크 격리와 Dev/Prod 환경 분리 적용 반영.
> ⚠️ 현재 문서는 **dev 환경을 중심으로 실행 상태를 기록**하고, 하단 `Dev/Prod 환경 분리` 섹션에서 prod 구성 상태를 별도로 정리한다.
> Dev/Prod는 Terraform state·tfvars·Secret·DB·도메인을 분리했으며, prod 전용 CD 파이프라인과 prod OAuth 콘솔 등록은 후속 항목이다.

## 1. 전체 요약

| 항목 | 현재 상태 |
| --- | --- |
| AWS Region | `ap-northeast-2` |
| IaC | Terraform |
| 배포 대상 | ECS Fargate |
| 기준 브랜치 | `develop` |
| Backend 상태 | ECS Service 실행 중 |
| Frontend 상태 | Frontend ECS 제거 완료, `https://badasoft.com`은 Backend 폴백 |
| Worker 상태 | SQS consumer 상시 실행, 분석·STT·PDF E2E 처리 완료, **1 vCPU / 2048 MiB 상향 적용** |
| DB | 운영 App DB를 encrypted Multi-AZ RDS PostgreSQL로 cutover 완료, 기존 Single-AZ DB는 rollback용 보존 |
| 파일 저장소 | S3 Evidence / Report Bucket |
| 비밀값 관리 | Secrets Manager |
| 설정값 관리 | SSM Parameter Store |
| 인증 인프라 | 소셜 OAuth(구글/카카오/네이버) 직접 구현으로 **전환 완료** (앱 계층 단일화 — `/auth/{provider}/login·callback` + `bada://` 딥링크 토큰, `AUTH_MODE=oauth`). Cognito는 **앱에서 미사용**이나, Terraform은 여전히 User Pool/Client/Domain + SSM `cognito/*` 파라미터를 생성하고 백엔드 태스크에 `COGNITO_*` 환경변수를 주입한다(레거시 잔존). 종료 시 정리 대상 |
| HTTPS/도메인 | `badasoft.com` ACM 인증서(ISSUED), ALB 443 리스너(TLS1.3), HTTP→HTTPS 301, Route 53 적용 완료 |
| Bedrock 모델 접근 | Anthropic FTU 제출 및 Claude Sonnet 4.6 Playground 호출 완료 |
| 팀원 모델 테스트 | 팀원 IAM 호출 권한 검증 완료, 모델 액세스는 자동 활성화(Model access 페이지 폐지)·IAM/SCP 통제 / `BEDROCK_MODEL_ID` 전환 |
| 배포 자동화 | Backend/Worker GitHub Actions OIDC 배포, Mobile EAS Build, Terraform Plan-in-PR 및 AWS 권한 반영 |
| 롤백 | Backend 수동 workflow + Worker·Grafana ECS CLI, Backend·Worker 자동 circuit breaker (`docs/runbooks/rollback-and-recovery.md`) |
| 모니터링 | Prometheus + Grafana ECS, CloudWatch datasource, Logs/Alarms/SNS/MCP, Grafana Task Role의 Alarm SNS Topic 한정 `sns:Publish`, Grafana `BADA-SNS` Contact Point·G1~G8 Rule·Notification Policy 적용 완료, **Container Insights 활성화**, **Worker Prometheus 메트릭 수집 적용 완료**(Cloud Map `worker.bada-dev.local` + 9090 scrape), **dev 스택에서 prod 크로스 환경 관측 추가**(PR #252: prod backend 공인 ALB Prometheus 스크랩 + Grafana `BADA Prod Infrastructure` CloudWatch 대시보드, `prod_monitoring_enabled` 토글, 기본 off — apply·활성화는 인프라 담당 예정) |
| X-Ray 분산 추적 | ECS Task Role X-Ray 권한, X-Ray daemon sidecar, `/aws/ecs/bada-dev/xray` Log Group 적용. PR #187 이후 Backend/Worker 모두 안전한 수동 segment 방식으로 전환했으며 Terraform에서 `backend_xray_enabled=true`, `worker_xray_enabled=true` 기준으로 재활성화 |
| Week 3 복구 검증 | Worker 재시도·DLQ·재시작 멱등성 검증, ALB 로그 30일 보존 적용 완료 (PR #60) |
| Week 3 운영 런북·Grafana 권한 | 팀 공용 장애·롤백 런북과 Alarm SNS Topic 한정 Publish 권한 반영 완료 (PR #61) |
| PR #63~모니터링 후속 검증 | Backend CD의 운영 HTTPS 200 게이트 성공, Backend `:49`, Grafana `:6`, Terraform No changes, ECS/Target/Alarm/SQS 정상 |
| 종료·정책 계획 | RDS·IAM·ECR 권고 결정과 7/10 종료·민감 데이터 삭제 런북 작성, 팀 승인 대기 |
| Week 4 DB Multi-AZ 전환 | 완료 | 별도 encrypted Multi-AZ DB 생성, restore/canary 검증 후 Secrets Manager `database_url` 전환 및 Backend/Worker 재배포 완료 |
| Well-Architected | Workload 생성 및 초기 milestone 저장 완료 |
| ECS Auto Scaling | Backend CPU 70% + Worker SQS backlog-per-task Target Tracking (min=1/max=3), 서비스 `ignore_changes=[desired_count]` 안전판 적용 (PR #203) |
| ECS Task Role 분리 | Backend/Worker 서비스별 최소권한 Role — Backend=producer(SQS Send·증거 RW·Bedrock·Translate), Worker=consumer(SQS Receive/Delete·리포트 RW·Bedrock·Transcribe·Translate) (PR #205) |
| Worker 컴퓨트 유형 | `FARGATE_SPOT` 전환(비용 절감, SQS+DLQ 멱등성으로 중단 안전), On-Demand base 토글 가능; Backend는 On-Demand 유지 (PR #206) |
| 보안 모니터링 | GuardDuty(S3 logs 탐지) + Security Hub(FSBP) + GuardDuty HIGH severity→SNS, `security_monitoring_enabled` 종료 토글 (PR #207) |
| WAF | AWS WAF v2 — IP평판 + OWASP Common + KnownBadInputs 3종 관리형 룰셋, ALB 연결, 로그 CloudWatch |
| 3-tier 네트워크 격리 | ALB/NAT는 public subnet, Backend/Worker/Grafana/Prometheus ECS Fargate와 RDS는 private subnet. ECS public IP 제거, NAT Gateway egress + S3 Gateway Endpoint 적용 |

## 2. 현재 실행 상태

| 구분 | 상태 |
| --- | --- |
| Backend ECS Service | `desired=1`, `running=1`, Task `bada-dev-backend:122`, private subnet, public IP 없음 |
| Frontend ECS Service | 제거됨 (`frontend_enabled=false`) |
| Worker ECS Service | `desired=1`, `running=1`, Task `bada-dev-worker:60`, private subnet, public IP 없음, `FARGATE_SPOT`, 9090 metrics port 노출 |
| Prometheus ECS Service | `desired=1`, `running=1`, Task `bada-dev-prometheus:3`, private subnet, public IP 없음, Backend/Worker scrape 설정 적용 |
| Grafana ECS Service | `desired=1`, `running=1`, Task `bada-dev-grafana:15`, private subnet, public IP 없음, Target Group healthy |
| Grafana URL | `https://monitor.badasoft.com`, `/api/health` 200 |
| Frontend Task Definition | 제거됨 |
| Frontend Target Group | 제거됨 |
| Frontend URL | `https://badasoft.com` → Backend 폴백 |
| Backend Task Definition | `bada-dev-backend:122`, `XRAY_ENABLED=true`, `xray-daemon` sidecar, `GPS_RETENTION_DAYS=1095` |
| Worker Task Definition | `bada-dev-worker:60`, 최신 Worker image 기준, `XRAY_ENABLED=true`, `xray-daemon` sidecar, `9090/metrics` portMapping 적용 |
| Target Group | `healthy` |
| ALB `/health` | `200 {"status":"ok"}` |
| ALB `/version` | `200 {"name":"BADA","version":"0.1.0","auth_mode":"oauth","storage_mode":"s3"}` |

## 3. 아키텍처 흐름

```text
Users
  -> ALB
      -> badasoft.com -> ECS Fargate Backend (frontend fallback)
      -> api.badasoft.com -> ECS Fargate Backend
  -> RDS PostgreSQL / S3 / SQS / OAuth Secrets / SSM / CloudWatch

SQS
  -> ECS Fargate Worker
  -> AI / OCR / Translation
  -> RDS PostgreSQL / S3
```

Worker는 장기 실행 SQS consumer로 상시 실행되며 분석, 음성 전사, PDF 생성 메시지를 처리한다.

## 4. 리소스 구현 현황

### Network

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| VPC | 완료 | BADA dev 인프라 기본 네트워크 |
| Public Subnet 2개 | 완료 | ALB / NAT Gateway 배치 |
| Private Subnet 2개 | 완료 | ECS(Backend/Worker/Grafana/Prometheus) + RDS 배치 |
| Internet Gateway | 완료 | Public subnet 외부 통신 |
| Route Table / Association | 완료 | Public / Private routing 분리, private RT `0.0.0.0/0 -> NAT` |
| NAT Gateway | 완료 | private subnet egress(EIP 43.202.234.217, nat-09b37a60c53a78da7), 0.0.0.0/0->NAT, `nat_gateway_enabled`/`ecs_in_private_subnets` 종료 토글 (2026-07-03) |
| VPC S3 Gateway Endpoint | 완료 | S3 트래픽 VPC 내부 경로 처리(무료, NAT 미경유), public/private RT 연결, `s3_gateway_endpoint_enabled` 종료 토글 (2026-07-02) |

#### 3-Tier 네트워크 격리 (2026-07-03 적용)

3-tier 네트워크 격리를 적용해 계층별로 서브넷을 분리했다.

- **Public tier**: ALB + NAT Gateway만 public subnet에 배치.
- **Private tier (ECS)**: Backend/Worker/Grafana/Prometheus 4개 서비스를 private subnet으로 이전, `assign_public_ip=false`. 외부 egress는 NAT Gateway(EIP `43.202.234.217`, `nat-09b37a60c53a78da7`)를 경유하고, private route table에 `0.0.0.0/0 -> NAT` 경로가 있다. S3 트래픽은 S3 Gateway Endpoint(`vpce-09ba7967a47b91555`)로 NAT를 우회한다.
- **Private tier (RDS)**: App DB는 이전부터 private subnet.
- **토글/롤백**: `nat_gateway_enabled=true`, `ecs_in_private_subnets=true`로 활성. 롤백은 `ecs_in_private_subnets=false`(ECS를 public으로 복귀). 7/10 종료 시 두 토글을 모두 `false`로 두어 NAT/EIP를 제거한다.

### Compute / Container

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| ECS Cluster | 완료 | Backend / Worker 공용 |
| Backend Task Definition | 완료 | `bada-dev-backend:122`, X-Ray 활성화, GPS 보존 1095일 설정 |
| Frontend Task Definition | 제거됨 | `frontend_enabled=false` 적용 이후 미운영 |
| Worker Task Definition | 완료 | `bada-dev-worker:60`, `DATABASE_URL`, S3 Report Bucket, SQS, AWS Provider, X-Ray daemon sidecar, 9090 Prometheus metrics port 적용 |
| Backend ECS Service | 실행 중 | `desired_count=1`, private subnet, public IP 없음, Auto Scaling min/max `1~3` |
| Frontend ECS Service | 제거됨 | `https://badasoft.com`은 Backend 폴백 |
| Worker ECS Service | 실행 중 | `desired_count=1`, private subnet, public IP 없음, `FARGATE_SPOT`, Auto Scaling min/max `1~3`, 분석·STT 메시지 처리 검증, `xray-daemon` RUNNING, Cloud Map `worker.bada-dev.local` 등록 |
| Backend ECR Repository | 완료 | Backend image 저장 |
| Frontend ECR Repository | 제거됨 | Frontend ECS 미사용과 함께 정리 |
| Worker ECR Repository | 완료 | Worker image 저장 |
| ALB | 완료 | `badasoft.com`, `api.badasoft.com`, `monitor.badasoft.com` 진입점 |
| Target Group | 완료 | Backend `/health` 중심, Grafana/Prometheus 별도 연결 |
| ECS Cluster Capacity Providers | 완료 | `FARGATE` + `FARGATE_SPOT` 연결, default 전략 On-Demand (PR #206) |
| Worker 컴퓨트 유형 | 완료 | `FARGATE_SPOT`(capacity_provider_strategy), `worker_fargate_ondemand_base`로 On-Demand base 지정 가능 (PR #206) |
| Backend Auto Scaling | 완료 | CPU 70% Target Tracking, min=1/max=3 (PR #203) |
| Worker Auto Scaling | 완료 | SQS backlog-per-task(`ApproximateNumberOfMessagesVisible / RunningTaskCount`) Target Tracking, min=1/max=3 (PR #203) |
| Backend Task Role | 완료 | 최소권한: 증거 S3 RW·리포트 R, SQS Send, KMS, Bedrock, Translate, X-Ray (PR #205) |
| Worker Task Role | 완료 | 최소권한: 증거 S3 R·리포트 RW, SQS Receive/Delete, KMS, Bedrock, Transcribe, Translate, X-Ray (PR #205) |

### Data / Storage / Queue

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| RDS PostgreSQL | 완료 | App DB는 `bada-dev-postgres-multiaz`(Multi-AZ, encrypted), 기존 `bada-dev-postgres`는 rollback용 보존 |
| RDS Multi-AZ 전환 | 완료 | dump/restore, row count, PostGIS/Alembic, Backend/Worker canary, Secret cutover, ECS 재배포 검증 완료 |
| RDS Deletion Protection | 완료 | 실수 삭제 방지 |
| RDS Automated Backup | 완료 | 7일 보존 |
| RDS Final Snapshot | 완료 | 삭제 시 최종 스냅샷 생성 |
| RDS Storage Encryption | 완료(App DB 기준) | 신규 Multi-AZ DB는 encrypted. 기존 Single-AZ DB는 rollback용 비암호화 상태로 임시 보존 |
| PostGIS Extension | 완료 | GPS 위치 데이터 확장 대비 |
| S3 Evidence Bucket | 완료 | 증거 파일 저장 |
| S3 Report Bucket | 완료 | 생성 리포트 저장 |
| S3 SSE-KMS | 완료 | 버킷 암호화 |
| S3 ALB Log Bucket | 완료 | `alb/` access log 30일 후 만료, 미완료 multipart upload 7일 후 정리 |
| S3 Evidence/Report/GPS Lifecycle | 완료 | Evidence `cases/`와 Report는 STANDARD_IA(90d)→GLACIER(365d), Evidence `gps-archive/`는 즉시 GLACIER_IR, MPU 7일 정리, `s3_lifecycle_enabled` 토글. 만료(파기)는 앱 레벨 분리 (2026-07-02) |
| SQS Analysis Queue | 완료 | Visibility Timeout 15분 / Long Polling 20초 적용 |
| SQS DLQ | 완료 | `maxReceiveCount=5`, 반복 실패 메시지 격리와 테스트 후 정리 검증 |

### Auth / Config / Secret

> ℹ️ 아래 Cognito 리소스는 Terraform에 의해 실제 생성되지만 **앱 로그인 경로에서는 미사용**이다(소셜 OAuth 직접 구현으로 전환). 레거시 잔존 리소스이며 종료 시 정리 대상이다.

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| Cognito User Pool | 완료(미사용 레거시) | `ap-northeast-2_5K39SlMFg` |
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
COGNITO_REDIRECT_URI=https://api.badasoft.com/auth/cognito/callback
COGNITO_LOGOUT_URI=https://badasoft.com/
COGNITO_SCOPES=openid email profile
```

- 기존 App Client를 인플레이스 수정해 Client ID를 유지했다.
- Google IdP는 `email`, `email_verified`, `name`, `username(sub)` 속성 매핑을 사용한다.
- Google Client Secret은 비추적 `infra/terraform.tfvars`와 암호화된 Terraform remote state에서만 관리한다.
- ⚠️ 위 Cognito 연동값은 **초기 방식(`AUTH_MODE=cognito`)** 이며, 현재 앱은 소셜 OAuth 직접 구현(`AUTH_MODE=oauth`)으로 전환됐다. Cognito User Pool/Client/Domain(+ Google IdP)과 SSM `cognito/*` 파라미터, 백엔드 `COGNITO_*` 환경변수는 **미사용 상태로 잔존**하며 종료 시 정리 대상이다.
- (과거 검증 기록) 초기 Cognito 방식에서 Hosted UI Google OAuth 진입, PKCE challenge, HTTPS callback, Secure cookie, Backend `AUTH_MODE=cognito` 적용을 확인했다.
- 실제 Google 사용자 계정의 로그인 완료, 보호 API 호출과 모바일 앱 복귀는 인증·모바일 담당 통합 테스트 범위다.

### AI / Bedrock

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| Anthropic First Time Use | 완료 | 팀 AWS 계정에서 use case details 제출 |
| 대상 모델 | 완료 | `global.anthropic.claude-sonnet-4-6` |
| Playground 호출 | 완료 | 서울 리전에서 정상 응답 확인 |
| ECS Task Role 권한 | 완료 | `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` |
| 애플리케이션 호출 | 코드 준비 완료 | 에이전트 업로드 후 `/extract`로 OCR 트리거 연결(`category=auto` + fire-and-forget). CloudWatch Logs `Bedrock 응답` 실증만 대기 |

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

### Security (WAF / GuardDuty / Security Hub)

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| AWS WAF v2 | 완료 | ALB 연결. IP평판 + OWASP Common + KnownBadInputs 3종 관리형 룰셋, 로그 CloudWatch(`aws-waf-logs-bada-dev`) |
| GuardDuty | 완료 | Detector 활성(S3 logs 데이터소스). HIGH severity(≥7) Finding → EventBridge → SNS 알림. `security_monitoring_enabled` 종료 토글 (PR #207) |
| Security Hub | 완료 | 계정 활성 + FSBP(Foundational Security Best Practices) 표준 구독. 종료 토글 공유. 일부 컨트롤은 AWS Config 의존(미활성) |

### Observability / Cost

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| CloudWatch Log Group | 완료 | Backend / Worker 로그 |
| CloudWatch Alarm | 완료 | ALB, Backend·Frontend·Worker ECS, RDS, SQS 핵심 지표 14개 |
| SNS Alarm Topic | 완료 | Alarm 14개 ALARM/OK action 연결 완료 |
| SNS Email Subscription | 완료 | `badajoa0710@gmail.com`, 테스트 메시지 및 Alarm/OK 경로 검증 |
| Grafana SNS Publish 권한 | 완료 | Monitoring Task Role에서 `bada-dev-alarm-notifications` Topic에만 허용 |
| Grafana Alert Contact Point / Rule / Policy | 완료 | `BADA-SNS` Contact Point, G1~G8 Rule 8개, 기본 Notification Policy receiver `BADA-SNS` 확인. 이메일 실수신·OK 복구 확인은 수신함 기준 운영 검증 필요 |
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

배포 workflow와 수동 rollback workflow는 `https://api.badasoft.com/health`의 HTTP 상태 코드가 정확히 `200`인지 검증한다. HTTP→HTTPS 301을 성공으로 오인하던 기존 ALB HTTP 검증은 제거했다.

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
| 현재 실행 상태 | `desired_count=1`, `running_count=1` |
| AWS 권한 반영 | 완료. Deploy Role이 Backend / Worker ECR push 가능 |
| 실행 검증 | 완료. 분석·STT·PDF 처리, 실패 재시도·DLQ, 강제 재시작·멱등성 확인 |

Worker는 SQS long-running consumer로 상시 실행한다. 정상 분석·STT·PDF 처리뿐 아니라 실패 메시지가 반복 수신 후 DLQ로 이동하는 경로와 Task 강제 재시작 후 동일 사건 재처리 시 결과가 중복되지 않는 것을 확인했다.

Worker runtime 사전 준비:

```text
SQS Visibility Timeout : 30초 -> 900초
SQS Receive Wait Time   : 0초 -> 20초
Worker DATABASE_URL     : Secrets Manager database_url 주입
terraform validate      : Success
terraform apply         : Success
terraform plan          : No changes
Worker Task Definition  : bada-dev-worker:19
Worker Service          : desired=1, running=1
```

검증 기록:

```text
terraform apply : success
changed         : Worker 상시 실행과 런타임 설정 적용
terraform plan  : No changes
Worker service  : desired=1, running=1
Retry / DLQ     : maxReceiveCount=5 이후 격리, 테스트 메시지 정리 완료
Idempotency     : 동일 사건 재처리 후 분석 결과 1건 유지
```

주의: 현재 GitHub 기본 브랜치가 `main`이므로, `develop`에만 존재하는 신규 workflow는 GitHub Actions 수동 실행 목록에 바로 노출되지 않을 수 있다. Worker workflow 실제 실행 검증은 `worker/**` 변경이 `develop`에 push될 때 자동 실행되거나, workflow가 default branch에 반영된 뒤 수동 실행으로 진행한다.

### 모바일 앱 빌드 자동화

```text
workflow_dispatch (수동 실행 전용)
  -> GitHub Actions checkout
  -> Node.js 20 + npm ci
  -> i18n 번역 검증 (npm run check:i18n)
  -> Expo GitHub Action + EXPO_TOKEN 인증
  -> EAS Build Android (빌드 완료까지 대기)
  -> 설치/QR 링크를 Discord로 알림
```

| 항목 | 상태 |
| --- | --- |
| Workflow | `.github/workflows/build-mobile.yml` |
| Trigger | **수동 실행 전용 (`workflow_dispatch`)** — EAS 무료 빌드 월 15회 쿼터 절약 목적으로 자동 push 빌드 제거 |
| 인증 방식 | `EXPO_TOKEN` GitHub Secret |
| 빌드 방식 | Expo EAS Build (클라우드) |
| 기본 프로필 | `preview` (APK, 내부 배포) / `production` (AAB) |
| 수동 실행 옵션 | `preview`, `production` |
| 현재 동작 | 빌드 완료까지 대기 후 설치/QR 링크를 Discord로 알림 (`EAS_DISCORD_WEBHOOK_URL` 설정 시) |

이 workflow는 AWS 인프라를 변경하지 않는다. 모바일 앱 Android 빌드를 Expo 클라우드에 제출하는 자동화다. `preview`는 APK 테스트 배포용, `production`은 AAB 릴리스용으로 사용한다.

### Frontend 배포 상태

Frontend ECS 자동배포는 현재 운영 대상이 아니다. `frontend_enabled=false` 적용 이후 Frontend ECS/ECR/Target Group/Alarm/Log Group과 `deploy-dev-frontend.yml` 워크플로는 제거됐다.

| 항목 | 상태 |
| --- | --- |
| 현재 배포 방식 | Frontend ECS 미사용 |
| 서비스 진입 | `https://badasoft.com` → Backend 폴백 |
| Frontend workflow | 제거 완료 |
| 비고 | 모바일 앱 중심 운영 전환. 웹 프론트 재도입 시 별도 workflow 재설계 필요 |

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

### Worker · Grafana 수동 롤백 (ECS CLI)

Worker·Grafana는 전용 롤백 workflow가 없으므로 ECS CLI로 실행 전 검증한 ACTIVE Task Definition 후보를 적용한다. Backend·Worker는 deployment circuit breaker 자동 rollback이 활성이고, Prometheus·Grafana는 수동 stable 확인이 필요하다.

```bash
aws ecs update-service --region ap-northeast-2 --cluster bada-dev-cluster \
  --service <bada-dev-worker|bada-dev-grafana> --task-definition <family:revision>
aws ecs wait services-stable --region ap-northeast-2 --cluster bada-dev-cluster --services <service>
```

| 서비스 | ACTIVE 후보 예시(2026-06-25) | 롤백 후 필수 검증 |
| --- | --- | --- |
| Worker | `bada-dev-worker:18` | consumer 시작 로그 + 테스트 메시지 처리 + SQS/DLQ 정상 |
| Grafana | `bada-dev-grafana:5` 또는 기본형 `:1` | `https://monitor.badasoft.com/api/health` 200 + Contact Point·Rule·Policy 확인 |

후보가 ACTIVE라는 사실만으로 안정성이 보장되지는 않는다. image tag·변경 이력·DB 호환성을 실행 전에 재확인한다. 상세 절차는 `docs/runbooks/rollback-and-recovery.md`를 참고한다.

## 6. 현재 미구현 / 대기 항목

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| Worker SQS long-running consumer | 완료 | `desired=1`, 메시지 처리·삭제 및 DLQ 0건 확인 |
| Worker runtime 인프라 적용 | 완료 | SQS 설정, DB Secret, Service `:19`, `desired=1/running=1` 검증 |
| Worker 자동배포 실행 검증 | 완료 | 분석·STT·PDF 처리와 재시도·DLQ·재시작 멱등성 검증 |
| Amazon Transcribe 독립 모드 | 완료 | Backend `:20`, Worker `:7`에 `TRANSCRIBE_MODE=aws` 배포 및 ALB health 검증 |
| Anthropic Claude 계정 접근 | 완료 | FTU 제출 및 Global Claude Sonnet 4.6 Playground 호출 검증 |
| ECS Bedrock 실제 호출 | 코드 준비 완료 | 업로드 후 `/extract` OCR 트리거 연결. CloudWatch Logs `Bedrock 응답` 실증만 대기 (상세: §4 AI / Bedrock) |
| Cognito Hosted UI/OAuth 인프라 | 완료 | Hosted UI, Authorization Code Grant, callback/logout URL 적용 |
| Cognito Google IdP | 완료 | PR #39 코드 반영 후 Terraform apply, App Client provider와 Google redirect 검증 |
| Google IdP Terraform drift | 완료 | PR #45 merge, AWS 자동 보정값 명시 및 최종 plan `No changes` 검증 |
| 인증 방식 (로그인) | 완료 | 소셜 OAuth(구글/카카오/네이버) 직접 구현으로 전환 완료 — `/auth/{provider}/login·callback` + `bada://` 딥링크 토큰, `AUTH_MODE=oauth`. Cognito 미사용 협의(리소스는 종료 시 정리). 모바일 로그인 E2E 코드 완비(#19), APK 파이프라인 수동 빌드(#20) |
| Well-Architected 1차 답변 | 완료 | 57개 질문 답변 및 milestone #2 저장 |
| SNS 기반 알림 전송 | 완료 | 구독 확인, 테스트 메시지, Alarm → SNS 및 OK 복구 알림 경로 검증 |
| CloudWatch MCP | 완료 | `bada-mcp-readonly` 프로필로 Log Group/Alarm 실제 조회 및 S3 접근 거부 확인 |
| Frontend ECS 배포 | 완료 | Next.js 15.5.19, ECR/Task/Service/ALB host routing, `/api/health` 200 |
| Worker 분석·PDF E2E | 완료 | SQS 처리 후 사건 `completed`, KMS 암호화 Report S3 PDF 저장 |
| Amazon Transcribe E2E | 완료 | 한국어 MP3 Job `COMPLETED`, 전사문 DB 저장, SQS 메시지 삭제 |
| ECS 배포 자동 롤백 | 완료 | Backend·Frontend·Worker deployment circuit breaker와 rollback 활성화 |
| RDS 저장 암호화 | 완료 | encrypted Multi-AZ DB로 cutover 완료 (기존 비암호화 Single-AZ DB는 rollback용 보존) |
| ECR 이미지 스캔 | 부분 완료 | Frontend Critical 1/High 8, Backend Critical 1/High 3, Worker 최신 OCI index는 Scan 없음 |
| ECS Auto Scaling (#4) | 완료 | Backend CPU + Worker SQS backlog Target Tracking, `ignore_changes=[desired_count]` 안전판 (PR #203) |
| Task Role 분리 (#13) | 완료 | Backend/Worker 서비스별 최소권한 Role (PR #205) |
| Worker Fargate Spot (#15) | 완료 | `FARGATE_SPOT` capacity provider 전환 (PR #206) |
| GuardDuty / Security Hub (#11) | 완료 | 본체 + 종료 토글(`security_monitoring_enabled`) (PR #207) |
| Terraform Plan-in-PR (#16) | 완료 | `infra/**` PR에서 읽기전용 plan-role로 fmt/validate/plan 자동 실행·PR 코멘트 (2026-07-02 확인) |
| k6 부하 테스트 (#9) | 완료 (2026-07-02) | 3종 검증 — ① Backend CPU 폐쇄형 부하: CPU 100% 3분 지속 → AlarmHigh → **1→2 scale-out** ② 사용자 여정(읽기): ~29rps에서 **p95 ~30ms·에러 0%·CPU 22~36%**(I/O 바운드) ③ Worker SQS 적체: Visible 44k → backlog 알람 → **1→3 scale-out**. 스크립트 `load-test/` (PR #212/#213) |

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
| P0 | Worker SQS consumer 구현 후 Worker Service 기동 검증 | Reliability / Cost | 완료 (`desired=1`, 처리·DLQ·멱등성 검증) |
| P1 | RTO/RPO와 RDS restore rehearsal 절차 정의 | Reliability | 문서화 완료 (2026-07-02) — 확정 RTO≤2h/RPO≤24h + PITR 복원 실측 절차·워크시트 `docs/operations/rto-rpo-and-restore-rehearsal.md`. 타임드 리허설 실행은 담당자 |
| P1 | ECR image scan, dependency scan, CI 보안 검증 강화 | Security | CI 보안 검증(ruff/bandit/pytest-cov) 완료 (#17), ECR scan-on-push 활성. dependency scan(pip-audit) 완료 (#B-2). 저위험 취약점 범프 완료 (#B-3 부분 — requests/python-multipart/pypdf/jinja2/pytest). fastapi+starlette·weasyprint+pillow 메이저는 별도 PR |
| P1 | ECS Backend/Worker Auto Scaling과 부하 테스트 기준 수립 | Performance / Reliability | Auto Scaling 적용 완료 (#4, PR #203). 부하 테스트(k6, #9) **완료** — Backend 1→2, Worker 1→3 scale-out 실증, 읽기 여정은 I/O 바운드 확인 (PR #212/#213) |
| P2 | Cost allocation tag, Cost Explorer/CUR 기반 비용 분석 강화 | Cost Optimization | 완료 (2026-07-02) — provider `default_tags`(Project/Environment/ManagedBy) catch-all + 분석/캡처 절차 `docs/operations/cost-allocation-and-analysis.md`. 결제 계정 태그 활성화·캡처는 담당자 |
| P2 | S3 lifecycle/retention 정책과 데이터 분류 기준 구체화 | Security / Sustainability | 완료 (2026-07-02) — ALB 로그 30일 + Evidence/Report Lifecycle(IA 90d→Glacier 365d + MPU 정리, `s3_lifecycle_enabled` 토글). 법정 3년 파기는 사건 단위 앱 로직(별도) |
| P2 | GPS 로그 보존기간 3년 분리 + S3 아카이브 lifecycle 선반영 | Security / Sustainability | 정책 반영 완료 (PR #226) — `gps_retention_days`(3년, 소멸시효 기준)를 일반 `retention_days`(90일)와 분리. `evidence` 버킷에 `gps-archive/` prefix용 GLACIER_IR 즉시전환 규칙 추가(선반영, 대상 코드 없음). 실제 export/아카이빙 로직과 삭제 배치는 architecture.md 6항에 설계만 기록, 미구현 |

## 8. 통합 요약 (HA · 보안운영 · Terraform · 잔여 로드맵)

> 아래 항목은 기존 개별 설계 문서(고가용성 설계 / 보안·운영 계획 / Terraform 리팩터링 / 프로덕션 로드맵)를 이 마스터 문서로 통합하며 핵심만 압축한 것이다.

### HA(고가용성) 현황

- **RDS Multi-AZ**: `bada-dev-postgres-multiaz`(encrypted) cutover 완료, 자동 failover 30~60초.
- **Backend/Worker Auto Scaling**: min=1/max=3 (Backend CPU 70%, Worker SQS backlog-per-task), PR #203.
- **배포 안정성**: Backend/Worker deployment circuit breaker 자동 롤백, ECS 헬스체크 실패 시 Task 자동 교체.
- **기준선**: 상시 최소 single-Task(desired=1) 운영, 부하 시 scale-out. 남은 SPOF는 관측 계층(Prometheus/Grafana desired=1)으로 서비스 트래픽 영향 없음.
- **RTO/RPO·복원 리허설**은 단일 출처 `docs/operations/rto-rpo-and-restore-rehearsal.md` 참조(확정 RTO≤2h/RPO≤24h).

### 보안 운영(Security Ops) 현황

- **이미지 취약점**: ECR scan-on-push + CI pip-audit(SCA) 적용. 저위험 취약점 범프 완료(#B-3 부분), fastapi+starlette·weasyprint+pillow 메이저는 별도 PR 잔여.
- **Task Role 분리**: Backend=producer(SQS Send·증거 RW·Bedrock·Translate) / Worker=consumer(SQS Receive/Delete·리포트 RW·Bedrock·Transcribe·Translate), PR #205.
- **경계 보안**: WAF `bada-dev-web-acl`(ALB 연결, 관리형 룰 3종), GuardDuty + Security Hub(FSBP), HIGH severity→SNS, `security_monitoring_enabled` 종료 토글.
- 상세 리소스 상태는 §4 Security / Observability 표 참조.

### Terraform 구조 결정

- Terraform은 **단일 state + 파일 성격별 분리**(network/data/compute/observability/iam/monitoring/autoscaling/security/waf/github-actions.tf) 채택. 서비스별 state 분리는 dev/prod 환경 분리 시점으로 이월(현 규모엔 과함).

### 남은/이월 로드맵

종료 일정(7/10)·비용 대비 위험이 가치를 초과해 의도적으로 보류/이월한 항목만 남긴다. 대부분의 프로덕션 고도화 항목은 이미 완료됐다.

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| Terraform 서비스별 state 분리 (#5) | 이월 | dev/prod 환경 분리 시점에 검토(옵션 C). 현재는 단일 state + 파일 분리로 갈음 |
| VPC Interface Endpoint (SQS/ECR, #18) | 이월 | S3 Gateway(무료)는 완료. Interface(~$7)는 단독 실익 낮아 보류 |
| 확장 HA (RDS Read Replica, ElastiCache, Cross-AZ 배치 전략) | 이월 | 실사용자 유입(MAU 1,000+) 이후 |
| CloudFront (정적 캐싱) | 이월 | 웹 프론트 재도입 시 |
| Blue/Green(CodeDeploy)·Canary·Feature Flag | 이월 | circuit breaker 자동 롤백으로 갈음 |
| Secrets 자동 로테이션(90d) | 이월 | rotation Lambda 필요, dev 실익 낮음 |
| 법적 필수 앱 기능(회원 탈퇴·동의·자동 파기) | 앱 계층 공백 | 인프라 아님. 상세: `aidlc-docs/remaining-tasks-20260702.md` 카테고리 A |

## 9. 참고 문서

| 문서 | 목적 |
| --- | --- |
| `infra/README.md` | Terraform 실행 방법과 인프라 코드 구조 |
| `docs/operations/ownership.md` | 파트별 담당 영역 |
| `.github/workflows/deploy-dev.yml` | Backend 자동배포 workflow |
| `.github/workflows/deploy-dev-worker.yml` | Worker 자동배포 workflow |
| `.github/workflows/build-mobile.yml` | 모바일 앱 EAS Build workflow |
| `.github/workflows/rollback-dev-backend.yml` | Backend 수동 롤백 workflow |
| `docs/runbooks/rollback-and-recovery.md` | ECS 롤백·복구 절차 |
| `docs/runbooks/demo-incident-response.md` | 데모 핵심 경로 장애 진단·대응 |
| `docs/runbooks/rds-recovery.md` | RDS 복원·암호화 전환·rollback 절차 |
| `docs/runbooks/project-closure.md` | 프로젝트 종료·데이터 보존·비용 리소스 정리 |
| `docs/infra/worker-sizing.md` | Worker ECS Task 스펙 + OCR 병렬 동시성 산정 근거 |
| `docs/operations/rto-rpo-and-restore-rehearsal.md` | RTO/RPO 정의 + RDS 복원 리허설 측정 워크시트 (B-1) |
| `docs/operations/cost-allocation-and-analysis.md` | 비용 할당 태그 + Cost Explorer 분석 절차 (B-4) |
| `aidlc-docs/remaining-tasks-20260702.md` | 남은 태스크 정리 (카테고리 A/B/C + 실행 계층) |

## 10. Dev/Prod 환경 분리 (2026-07-03)

멘토 피드백을 반영해 기존 dev 환경과 독립된 prod 환경을 추가했다. 이제 BADA는 **2개 환경(dev + prod)** 을 운영한다. 이 섹션은 prod 구성 상태와 dev/prod 분리 기준을 별도로 기록한다.

### 환경 비교

| 환경 | 리소스 접두사 | 도메인 | tfstate key | tfvars / backend 파일 |
| --- | --- | --- | --- | --- |
| dev | `bada-dev-*` | `badasoft.com` (`api.` / `monitor.`) | `bada/dev/terraform.tfstate` | `terraform.tfvars` + `backends/dev.hcl` |
| prod | `bada-prod-*` | `prod.badasoft.com` (`api.prod.` / `monitor.prod.`) | `bada/prod/terraform.tfstate` | `env/prod.tfvars` + `backends/prod.hcl` |

### 분리 메커니즘

- **부분 백엔드 설정(partial backend config)**: `providers.tf`에서 백엔드 `key`를 제거하고 `backends/<env>.hcl`로 분리. 모듈 리팩터링 없이 구성했다. 환경 전환 시 `terraform init -reconfigure -backend-config=backends/<env>.hcl` 필수.
- **`environment` 변수**: 코드가 이미 `local.name_prefix = "${var.project_name}-${var.environment}"`로 파라미터화돼 있어 `environment=prod` apply만으로 `bada-prod-*` 리소스가 생성된다. dev state는 건드리지 않는다.
- **`route53_zone_name`**: prod 서브도메인(`prod.badasoft.com`) 레코드가 부모 존(`badasoft.com`)에 생성되도록 하는 변수(기본 `""`이면 `domain_name` 사용).

### prod 현재 상태

- ECS 4개 서비스(backend/worker/grafana/prometheus) rollout COMPLETED.
- RDS `bada-prod-postgres-multiaz` (Multi-AZ) available.
- `api.prod.badasoft.com/health` 200, `/version` `auth_mode=oauth`/`storage_mode=s3`, `monitor.prod.badasoft.com/api/health` 200.
- prod plan: 최초 144 add/0 change/0 destroy → 함정 수정 후 `No changes`. dev 재확인도 `No changes`(무손상).

### 계정 수준 공유 싱글턴

- GuardDuty / Security Hub는 **계정-리전 단위 싱글턴**으로 이미 dev state가 소유하며 계정 전체를 커버한다.
- 따라서 prod는 `security_monitoring_enabled=false`로 두어 중복 생성을 피한다.

### 크로스 환경 관측 (dev → prod, PR #252)

prod도 자체 Prometheus/Grafana 스택을 갖지만, **dev 단일 Grafana에서 양 환경을 함께 보기 위한 크로스 환경 관측**을 추가했다(환경별 state 분리로 dev Grafana가 prod를 못 보던 문제 해소). 크로스-VPC 네트워킹 없이 구성한다.

| 대상 | 방식 |
| --- | --- |
| prod backend 앱 메트릭 | Prometheus가 공인 ALB(`api.prod.badasoft.com/metrics`)를 인터넷(NAT egress) 경유로 스크랩, `env="prod"` 라벨 |
| prod ECS/RDS/ALB/SQS/Task Count | dev Grafana의 CloudWatch datasource가 prod 리소스 이름으로 조회(동일 계정·리전, 모니터링 Task Role CloudWatch read 재사용) → `BADA Prod Infrastructure` 대시보드 |
| prod worker 앱 메트릭 | 크로스-VPC Cloud Map 스크랩 불가 → CloudWatch(Container Insights)로 갈음 |

- **토글/안전판**: `prod_monitoring_enabled`(기본 `false`). off일 때는 `data.aws_lb.prod` 조회를 하지 않아 prod 미배포 상태에서도 dev plan/apply가 안전하다. on으로 켜려면 prod 스택(특히 `bada-prod-alb`)이 실제 배포돼 있어야 한다.
- **부작용 주의**: 켜면 `env` 라벨 없는 기존 알림 쿼리(G1·G3·G9 등)가 dev+prod를 합산한다. 환경 분리가 필요하면 쿼리에 `{env="dev"}`를 추가한다(`docs/operations/monitoring-guide.md` §9).
- **현재 상태**: 코드 병합 완료. `prod_monitoring_enabled=true` tfvars 설정 및 apply는 인프라 담당 예정.

### 이월 항목

- prod 전용 CD 파이프라인(현재 dev ECR `:latest` 참조, 수동 배포).
- prod OAuth 콜백 콘솔 등록(`api.prod.badasoft.com`).
- 잔여 Single-AZ `bada-prod-postgres` 정리 또는 primary `multi_az` 변수화.
