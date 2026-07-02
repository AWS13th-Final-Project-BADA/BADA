# BADA Terraform Infra

이 디렉토리는 BADA의 AWS 인프라를 Terraform으로 관리한다.

현재 범위:

- ECR
- VPC
- S3 + KMS
- SQS + DLQ
- RDS PostgreSQL
- Cognito
- ALB
- ECS Fargate
- Secrets Manager / SSM Parameter Store
- CloudWatch Logs / Alarms
- Prometheus + Grafana

기본 사용 순서:

```bash
cd infra
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

MVP 원칙:

- 리전은 `ap-northeast-2`
- AWS 관리형 서비스만 사용
- backend / worker는 ECS Fargate 기준
- API 진입점은 `ALB`
- 원본 증거는 S3 + KMS
- 분석 작업은 SQS (+ DLQ)
- `ALB / ECS public subnet`, `RDS private subnet`
- `NAT Gateway는 사용하지 않음`
- `RDS Single-AZ`로 시작
- 운영 DB는 유지하고, Multi-AZ 전환 검증은 별도 rehearsal DB(`bada-dev-postgres-multiaz`)에서 수행
- `RDS 삭제 보호`, `자동 백업 7일 보존`, `삭제 시 최종 스냅샷 생성` 적용
- RDS 생성 후 `bada` DB에 `postgis` extension 활성화
- Backend / Worker 이미지는 ECR `latest` 태그로 push 가능
- Backend ECS Service는 수동 검증 기준 `desired_count = 1`로 기동 및 ALB `/health` 200 응답 확인
- Worker ECS Service는 SQS consumer 검증 완료 후 `desired_count = 1`로 상시 실행
- Worker queue는 10분 전사 작업을 고려해 Visibility Timeout 15분, Long Polling 20초를 사용
- Worker Task는 Secrets Manager의 `database_url`을 `DATABASE_URL`로 주입
- Worker 자동배포 workflow는 Task Definition revision 갱신과 Service 안정화에 사용
- 오디오 전사는 Worker SQS consumer 완성 전까지 `TRANSCRIPTION_DISPATCH_MODE=inline`으로 Backend에서 직접 처리 가능하게 구성
- `TRANSCRIBE_MODE=aws`를 별도로 사용해 `PROVIDER_MODE=local` 상태에서도 Amazon Transcribe만 실제 호출 가능
- ECS Task Role에는 Bedrock/Translate 외에 Amazon Transcribe 호출 권한 포함
- ECS Task Role에는 X-Ray trace 전송 권한(`xray:PutTraceSegments`, `xray:PutTelemetryRecords`)도 포함한다.
- Worker는 `worker_xray_enabled=true`로 X-Ray daemon sidecar를 실행한다.
- Backend는 PR #187 이후 `backend_xray_enabled=true`로 전환 가능하다. PR #187은 `patch_all()`과 지원되지 않는 `begin_segment(http=...)` 호출을 제거하고 안전한 수동 segment 방식으로 바꿨다.
- CloudWatch Alarm은 ALB/ECS/RDS/SQS 핵심 지표 기준으로 생성하며, 기본은 콘솔 확인용이다.
- ALB access log는 S3에 저장하고 기본 30일 후 자동 만료한다.
- CloudWatch MCP는 Terraform 관리 최소권한 AssumeRole을 통해서만 AWS에 접근한다.
- Prometheus는 Fargate 로컬 볼륨에 3일간 저장하고, Grafana 데이터만 EFS에 영속화한다.
- Grafana는 Cloud Map의 `prometheus.bada-dev.local`을 통해 Prometheus에 접근한다.
- Prometheus는 Backend `/metrics`와 Worker `worker.bada-dev.local:9090/metrics`를 수집한다. Worker 대상은 Cloud Map service discovery와 ECS SG 9090 ingress로 연결한다.
- Grafana 관리자 비밀번호는 Terraform이 생성해 Secrets Manager `bada-dev/grafana-admin-password`에 저장한다.
- Cognito App Client는 Authorization Code Grant와 `openid email profile` scope를 사용한다.
- Google 로그인을 사용할 때는 Cognito Federated Identity Provider와 App Client provider를 Terraform으로 함께 관리한다.
- 프로젝트 운영 기간은 `2026-06-04 ~ 2026-07-10`, 팀 합의 예산은 `1,500달러`이며 현재 AWS Budget 가드레일은 `1,000달러`
- 기존 RDS는 `StorageEncrypted=false`다. 암호화 적용은 암호화 스냅샷 복사와 신규 RDS 복원·전환 작업으로 별도 수행한다.
- rehearsal RDS는 `storage_encrypted=true`, `multi_az=true`로 생성되며 현행 운영 DB와 앱 Secret에는 영향이 없다.
- IAM은 dev 계정에서는 개발 속도를 우선해 넓게 운영하고, 운영/프로덕션 전환 시 Access Advisor/CloudTrail 기반으로 최소권한을 재설계한다.

IAM 운영 기준:

```text
현재 dev 계정
  -> 팀원 콘솔 조회 / AWS CLI / terraform plan 허용 가능
  -> terraform apply는 인프라 담당자가 수행
  -> Terraform 관리 리소스는 콘솔 직접 수정 지양

운영/프로덕션 전환 시
  -> IAM Access Advisor / CloudTrail 사용 이력 확인
  -> 실제 사용 권한만 남긴 최소권한 정책으로 재설계
```

수동 배포 검증 결과:

```text
Backend ECS Service: desired=1, running=1
Worker ECS Service : desired=1, running=1, bada-dev-worker:55
Prometheus Service : desired=1, running=1, bada-dev-prometheus:3
Grafana Service    : desired=1, running=1, bada-dev-grafana:10
ALB /health        : 200 {"status":"ok"}
ALB /version       : 200 {"name":"BADA","version":"0.1.0","auth_mode":"oauth","storage_mode":"s3"}
S3 Evidence object : SSE-KMS 저장 확인
RDS schema         : alembic_version=20260616_0004, community tables/provider columns/timeline confidence 확인
Worker X-Ray       : XRAY_ENABLED=true, xray-daemon RUNNING
Backend X-Ray      : XRAY_ENABLED=true, xray-daemon RUNNING
Worker metrics     : 9090/metrics portMapping + Cloud Map worker.bada-dev.local 적용
```

Cognito Hosted UI / OAuth:

```text
User Pool ID : ap-northeast-2_5K39SlMFg
Client ID    : 2n7fd1lbtifh3d3269i400es1f
Domain       : https://bada-dev-165749212250.auth.ap-northeast-2.amazoncognito.com/
Callback URL : https://api.badasoft.com/auth/cognito/callback
Sign-out URL : https://badasoft.com/
OAuth Flow   : Authorization code grant
Scopes       : openid email profile
```

- Terraform은 Hosted UI Domain, App Client OAuth 설정, Backend ECS 환경변수, SSM Parameter를 관리한다.
- 기존 App Client를 인플레이스 수정해 Client ID를 유지했다.
- 인프라 적용과 `terraform plan`의 `No changes` 검증은 완료됐다.
- Backend는 callback/code 교환, PKCE, JWT/JWKS 검증 코드와 `AUTH_MODE=cognito`가 배포됐다. 실제 사용자 로그인과 모바일 앱 복귀는 팀 통합 테스트에서 확인한다.

Google Identity Provider 활성화:

```hcl
# infra/terraform.tfvars (Git 추적 제외)
enable_google_identity_provider = true
google_oauth_client_id           = "your-client-id.apps.googleusercontent.com"
google_oauth_client_secret       = "your-client-secret"
```

- Google OAuth redirect URI는 `https://<cognito-domain>/oauth2/idpresponse`로 등록한다.
- Cognito는 Google의 `email`, `name`, `email_verified`, `sub`를 User Pool의 `email`, `name`, `email_verified`, `username`에 매핑한다.
- Google Client Secret은 Git, PR, 문서에 기록하지 않고 비추적 `terraform.tfvars`에서만 주입한다.
- 팀 AWS 계정에 Terraform apply를 완료했으며 기존 App Client ID를 유지한 채 `COGNITO`, `Google` provider가 활성화됐다.
- Hosted UI authorize 요청이 Google OAuth endpoint로 HTTP `302` 리다이렉트되는 것을 확인했다.
- AWS가 자동 보완하는 Google endpoint metadata와 `username = sub` 매핑은 Terraform에 명시해 후속 plan drift를 방지한다.
- 실제 Google 사용자 로그인, callback code 교환과 JWT 검증은 인증 담당자가 검증한다.

Bedrock Anthropic 모델 접근:

- 팀 AWS 계정에서 Anthropic First Time Use(FTU) use case details 제출을 완료했다.
- `ap-northeast-2` Bedrock Playground에서 `global.anthropic.claude-sonnet-4-6` 호출을 검증했다.
- FTU 제출은 계정 단위 최초 1회 운영 절차이며 Terraform 리소스로 관리하지 않는다.
- ECS Task Role의 `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` 권한은 Terraform으로 관리한다.
- 다음 검증 단계는 실제 Backend/Worker Task Role을 통한 Claude 호출과 CloudWatch Logs 확인이다.

팀원 Bedrock 모델 자유 테스트:

- OCR/음성인식 담당자가 후보를 미리 정하지 않고 여러 모델을 바꿔가며 테스트할 수 있게 구성한다.
- Bedrock 호출은 `IAM 권한`과 `모델 액세스` 두 층을 통과해야 한다.
- 팀원 4명은 `BADA-Developers` 그룹의 `PowerUserAccess`로 `bedrock:InvokeModel` 등 호출 권한을 이미 충족한다(simulate-principal-policy로 검증).
- Bedrock `Model access` 수동 활성화 페이지는 폐지됐고(`Model access page has been retired`), 서버리스 파운데이션 모델은 계정에서 처음 호출되는 순간 자동 활성화된다.
- 예외는 Anthropic 모델의 first-time use case 제출(이미 완료)과 AWS Marketplace 경유 모델의 최초 1회 invoke뿐이다.
- 모델 접근 통제는 콘솔 토글이 아니라 IAM 정책/SCP로 한다. 넓게 열려면 현재 PowerUserAccess로 충분하고, 좁히려면 모델 ARN 화이트리스트 IAM 정책이나 SCP를 사용한다.
- 앱은 모델을 `BEDROCK_MODEL_ID` 환경변수로 지정하므로(`worker/config.py`, 기본값 `global.anthropic.claude-sonnet-4-6`), 팀원은 로컬에서 이 값만 바꿔 모델을 교체한다.
- `global.` / `apac.` cross-region inference profile은 라우팅 대상 리전에서도 모델이 사용 가능해야 하므로 리전 내 on-demand 모델 ID 사용을 권장한다.
- 자동 활성화로 어떤 모델이든 쉽게 호출되므로 고가 모델(예: Opus 계열) 반복 호출에 대비해 AWS Budgets의 Bedrock 비용 알림을 안전망으로 둔다.

모델 사용/검증 절차(현재 기준):

```text
Amazon Bedrock (리전 ap-northeast-2)
  -> 모델 카탈로그에서 모델 선택 후 Playground 실행
     또는 bedrock-runtime invoke-model / Converse API로 직접 호출
  -> 첫 호출 시 서버리스 모델 자동 활성화
  -> 응답 확인으로 사용 가능 여부 검증
  (Anthropic은 FTU 1회 완료, Marketplace 모델만 최초 1회 invoke 필요)
```

GitHub Actions Backend 자동배포:

```text
develop push
  -> OIDC Role assume
  -> Backend Docker image build / ECR push
  -> ECS Task Definition 새 revision 등록
  -> ECS Service update
  -> https://api.badasoft.com/health 확인
```

- Workflow: `.github/workflows/deploy-dev.yml`
- 배포 후 `https://api.badasoft.com/health`가 정확히 HTTP 200인지 확인한다.
- Deploy Role: `arn:aws:iam::165749212250:role/bada-dev-github-actions-deploy-role`
- Trigger: `develop` push 또는 수동 실행
- Scope: Backend ECS Service 우선 배포
- Health Check: 고정 URL `https://api.badasoft.com/health`에 대해 HTTP 200을 검증
- Terraform은 ECS Service 골격을 관리하고, 배포 후 task definition revision 변경은 GitHub Actions가 관리한다. 따라서 ECS Service의 `task_definition` drift는 Terraform에서 무시한다.

GitHub Actions Worker 자동배포:

```text
develop push
  -> OIDC Role assume
  -> Worker Docker image build / ECR push
  -> ECS Task Definition 새 revision 등록
  -> ECS Service update
  -> ECS Service 상태 출력
```

- Workflow: `.github/workflows/deploy-dev-worker.yml`
- Deploy Role: `arn:aws:iam::165749212250:role/bada-dev-github-actions-deploy-role`
- Trigger: `worker/**` 변경이 포함된 `develop` push 또는 수동 실행
- Scope: Worker ECS Service 배포 준비
- 현재 기준: Worker SQS consumer 검증 완료, `desired_count = 1`
- 의미: image build, ECR push, task definition revision 갱신 후 상시 Worker Service로 배포한다.

Worker runtime 사전 준비:

```text
SQS visibility_timeout_seconds : 900
SQS receive_wait_time_seconds  : 20
Worker secret                  : DATABASE_URL
Secret source                  : bada-dev/app-secrets의 database_url
Current Worker Service         : desired=1, running=1
Current Worker Task Definition : bada-dev-worker:17
```

- Visibility Timeout은 현재 전사 서비스의 최대 대기 시간 10분보다 5분 길게 잡아 처리 중 메시지가 조기에 재노출되는 위험을 줄인다.
- Long Polling 20초는 빈 큐를 반복 조회하는 요청 수와 불필요한 비용을 줄인다.
- Terraform apply와 AWS 속성 조회를 통해 SQS 설정과 Worker Secret 주입을 검증했다.
- 새 Task Definition 등록 후 ECS Service가 이전 revision을 유지해, Service 참조를 `bada-dev-worker:4`로 갱신했다.
- 최종 `terraform plan`은 `No changes`를 확인했다.
- Worker Docker CMD는 SQS consumer를 실행하고, `worker_desired_count=1`, `TRANSCRIPTION_DISPATCH_MODE=sqs`를 사용한다.

Amazon Transcribe 독립 모드:

```text
Backend PROVIDER_MODE              : local
Backend TRANSCRIBE_MODE            : aws
Backend TRANSCRIPTION_DISPATCH_MODE: inline
Worker PROVIDER_MODE               : local
Worker TRANSCRIBE_MODE             : aws
```

- `TRANSCRIBE_MODE`를 생략하면 기존처럼 `PROVIDER_MODE`를 상속한다.
- Backend는 현재 inline 전사 경로에서 실제 Amazon Transcribe를 호출한다.
- Worker는 Consumer 실행 전이므로 설정만 준비하고 `desired_count=0`을 유지한다.
- PR #36 머지 후 Backend `bada-dev-backend:20`, Worker `bada-dev-worker:7` 자동배포에 성공했다.
- Backend와 Worker Service는 모두 `desired=1/running=1`, ALB `/health`는 200을 확인했다.

Worker 자동배포 권한 반영 결과:

```text
Terraform apply : success
Changed         : GitHub Actions Deploy Role policy 1개
ECR push scope  : bada-dev-backend, bada-dev-worker
Terraform plan  : No changes
Worker Service  : desired=1, running=1
```

주의:

- Worker workflow는 `worker/**` 변경이 포함된 `develop` push에서 실제 실행되어 image push, Task Definition revision 등록, Service update 흐름을 확인했다.
- Worker Service는 consumer 검증 완료 후 `desired_count = 1`을 유지한다.

GitHub Actions 수동 롤백:

```text
Rollback Dev Backend workflow_dispatch
  -> OIDC Role assume
  -> 입력한 ECS Task Definition 존재 확인
  -> ECS Backend Service를 해당 revision으로 update-service
  -> services-stable 대기
  -> ALB /health 재검증
```

- Workflow: `.github/workflows/rollback-dev-backend.yml`
- 롤백 후 `https://api.badasoft.com/health`가 정확히 HTTP 200인지 확인한다.
- 실행 브랜치: `develop`
- 입력값 예시: `bada-dev-backend:9` 또는 Task Definition ARN
- 사용 시점: 새 배포 후 `/health` 실패, 주요 API 장애, CloudWatch 로그에서 기동 오류가 확인될 때
- 주의: 롤백은 ECS Service가 참조하는 Task Definition revision만 되돌린다. DB migration, S3 데이터, Secrets 값 변경은 자동으로 되돌리지 않는다.

자동배포 검증 결과:

```text
PR #31 merge 이후 develop push 기준 실행 성공
CI workflow     : success
Deploy workflow : success
Backend task def: bada-dev-backend:17
ECS state       : desired=1, running=1, rolloutState=COMPLETED
ALB /health     : 200 {"status":"ok"}
```

인프라 보강 적용 결과:

```text
Terraform apply : success
Terraform 기준 Backend task def: bada-dev-backend:7
현재 ECS Service task def     : bada-dev-backend:9
추가 환경변수    : TRANSCRIPTION_DISPATCH_MODE=inline
추가 IAM 권한   : transcribe:Start/Get/Delete/ListTranscriptionJob
GitHub Actions : PR #24 merge 후 bada-dev-backend:9로 코드 배포 완료
```

팀원 기능 smoke test:

```text
POST /cases                                      : 200
POST /community/posts                           : 200
POST /cases/{case_id}/evidences/agent-upload    : 200
GET  /cases/{case_id}/evidences                 : 200
POST /cases/{case_id}/evidences/scan            : 200
CloudWatch Logs                                 : 요청 로그 확인
```

CloudWatch Alarm 기본 세트:

```text
ALB Target 5xx              : 5분 동안 5건 이상
ALB Unhealthy Targets       : 1개 이상
Backend ECS CPU             : 80% 이상
Backend ECS Memory          : 80% 이상
RDS CPU                     : 80% 이상
RDS Free Storage            : 5 GiB 미만
SQS Analysis Backlog        : visible message 10개 이상
SQS Analysis DLQ            : visible message 1개 이상
```

- 기본값은 `alarm_email_endpoints = []`, `alarm_actions = []`이며 실제 이메일 주소는 Git에서 제외되는 로컬 `terraform.tfvars`에만 저장한다.
- SNS Topic `bada-dev-alarm-notifications`는 Terraform apply로 생성 완료했다.
- 팀 알림 이메일 `badajoa0710@gmail.com` 구독을 생성하고 CloudWatch Alarm 14개의 `alarm_actions`와 `ok_actions`에 SNS Topic을 연결했다.
- Grafana Monitoring Task Role에는 해당 Alarm Topic 하나로 제한한 `sns:Publish` 권한을 적용했다.
- Grafana Contact Point와 Alert Rule은 모니터링 담당의 임계치·수신자 확정 후 구성하고 실제 이메일 수신을 검증한다.
- Backend·Frontend·Worker ECS Service는 deployment circuit breaker와 자동 rollback을 사용한다.
- SQS 메시지 수뿐 아니라 `ApproximateAgeOfOldestMessage >= 600초`도 감시해 적은 수의 정체 메시지를 탐지한다.

컨테이너 이미지 보안 확인:

- ECR 3개 저장소는 `scan_on_push = true`다.
- Frontend 최신 이미지 스캔에서 Alpine OpenSSL 계열 Critical 1건과 High 8건이 확인됐으며, ECR 결과상 fixed version은 아직 없다.
- Backend 최신 Docker v2 이미지 스캔은 Critical 1건, High 3건이다.
- Worker 최신 이미지는 OCI image index라 Scan 결과가 없다.
- GitHub Actions build는 `--provenance=false`를 사용한다. 다음 CD 배포에서 Docker v2 manifest와 스캔 결과를 재확인한다.
- 이메일 구독 confirmation, SNS 테스트 메시지, CloudWatch Alarm/OK 알림 수신 경로를 검증했다.
- 확장: `alarm_email_endpoints`에 이메일 주소를 넣으면 Terraform 관리 SNS Topic에 이메일 구독을 생성하고, CloudWatch Alarm action에 연결한다.
- 주의: 이메일 구독자는 AWS SNS confirmation 메일을 반드시 승인해야 실제 알림을 받을 수 있다.
- 별도 SNS Topic을 이미 운영 중이면 `alarm_actions`에 기존 action ARN을 추가할 수 있다.
- 적용 결과: `terraform apply`로 8개 알람 생성 완료, 이후 `terraform plan` 기준 `No changes` 확인
- 참고: 생성 직후에는 CloudWatch metric 데이터가 충분하지 않아 `INSUFFICIENT_DATA`로 보일 수 있다.

CloudWatch MCP 운영:

```text
IAM Role    : bada-dev-mcp-cloudwatch-readonly-role
AWS Profile : bada-mcp-readonly
Region      : ap-northeast-2
Runtime     : uvx + Python 3.10
Server      : awslabs.cloudwatch-mcp-server 1.28.0 (검증 시점)
```

- MCP Role은 CloudWatch Alarm/Metric 조회와 CloudWatch Logs 조회·Insights Query에 필요한 작업만 허용한다.
- 전용 profile의 CloudWatch 조회 성공과 S3 `AccessDenied`를 함께 확인해 최소권한 경계를 검증했다.
- Logs Insights는 읽기 작업이지만 사용량 비용이 발생할 수 있으므로 Codex 도구 기본 승인은 `prompt`로 유지한다.
- MCP 검증 결과 Backend/Worker Log Group 조회와 활성 Alarm 0개 확인에 성공했다.
- Terraform 적용 결과는 `2 added, 0 changed, 0 destroyed`, 후속 plan은 `No changes`였다.

알림 이메일 설정 예시:

```hcl
alarm_email_endpoints = [
  "badajoa0710@gmail.com"
]
```

현재 적용 결과:

```text
SNS Topic        : bada-dev-alarm-notifications
Email endpoint   : badajoa0710@gmail.com
Subscription     : PendingConfirmation
Connected alarms : 8
Terraform plan   : No changes
```

confirmation 완료 후 SNS Topic에 테스트 메시지를 publish해 실제 수신까지 확인한다.

Well-Architected Tool 등록:

```text
Workload Name     : BADA Dev Infrastructure
Workload ID       : 95748e8dbd2cc80821d6429d20a9ef03
Environment       : PREPRODUCTION
Region            : ap-northeast-2
Lens              : AWS Well-Architected Framework
Initial Milestone : 2026-06-17 initial workload baseline
Review Milestone  : 2026-06-17 first review answers
Milestone Number  : 1, 2
Question status   : 57 answered
Risk summary      : HIGH 30 / MEDIUM 24 / NONE 3 / UNANSWERED 0
```

- workload를 생성하고 초기 milestone과 1차 답변 milestone을 저장했다.
- 답변은 현재 구현된 dev/pre-production 인프라 기준으로 보수적으로 선택했다.
- High Risk는 대부분 MVP 일정과 비용 때문에 의도적으로 미룬 HTTPS, 알림, DR 테스트, 오토스케일링, 보안 스캔, 비용 상세 분석 항목이다.
- 처음 생성 시 `IndustryType=Technology`는 AWS 허용 값이 아니어서 실패했고, `InfoTech`로 생성했다.

우선 개선 항목:

- P0: ALB HTTPS/ACM 적용 및 HTTP -> HTTPS redirect 검토
- P0: CloudWatch Alarm SNS 이메일 수신 검증 완료
- P0: Worker SQS consumer 구현 후 Worker Service 기동 검증
- P1: RTO/RPO와 RDS restore rehearsal 절차 정의
- P1: ECR image scan, dependency scan, CI 보안 검증 강화
- P1: ECS Backend/Worker Auto Scaling과 부하 테스트 기준 수립

롤백 대상 revision 확인:

```bash
aws ecs list-task-definitions \
  --region ap-northeast-2 \
  --family-prefix bada-dev-backend \
  --sort DESC \
  --max-items 10
```

주의: `terraform.tfvars`는 로컬 전용 파일이며 GitHub에 커밋하지 않는다. Backend task를 계속 실행하면 Fargate 비용이 발생하므로 검증 종료 후 필요 시 `backend_desired_count = 0`으로 되돌린다.
주의: GitHub Actions가 배포한 최신 Backend revision을 Terraform apply가 과거 revision으로 되돌리지 않도록, ECS Service `task_definition`은 `ignore_changes`로 관리한다.
