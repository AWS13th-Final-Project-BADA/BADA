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
- `RDS 삭제 보호`, `자동 백업 7일 보존`, `삭제 시 최종 스냅샷 생성` 적용
- RDS 생성 후 `bada` DB에 `postgis` extension 활성화
- Backend / Worker 이미지는 ECR `latest` 태그로 push 가능
- Backend ECS Service는 수동 검증 기준 `desired_count = 1`로 기동 및 ALB `/health` 200 응답 확인
- Worker ECS Service는 SQS consumer 검증 전까지 `desired_count = 0` 유지
- 오디오 전사는 Worker SQS consumer 완성 전까지 `TRANSCRIPTION_DISPATCH_MODE=inline`으로 Backend에서 직접 처리 가능하게 구성
- ECS Task Role에는 Bedrock/Translate 외에 Amazon Transcribe 호출 권한 포함
- CloudWatch Alarm은 ALB/ECS/RDS/SQS 핵심 지표 기준으로 생성하며, 기본은 콘솔 확인용이다.
- 프로젝트 운영 기간은 `2026-06-04 ~ 2026-07-10`, 팀 전체 AWS 총 예산은 `1,500달러`
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
Worker ECS Service : desired=0, running=0
ALB /health        : 200 {"status":"ok"}
ALB /version       : 200 {"name":"BADA","version":"0.1.0","auth_mode":"demo","storage_mode":"s3"}
S3 Evidence object : SSE-KMS 저장 확인
RDS schema         : alembic_version=20260616_0004, community tables/provider columns/timeline confidence 확인
```

GitHub Actions 자동배포:

```text
develop push
  -> OIDC Role assume
  -> Backend Docker image build / ECR push
  -> ECS Task Definition 새 revision 등록
  -> ECS Service update
  -> ALB DNS lookup
  -> ALB /health check
```

- Workflow: `.github/workflows/deploy-dev.yml`
- Deploy Role: `arn:aws:iam::165749212250:role/bada-dev-github-actions-deploy-role`
- Trigger: `develop` push 또는 수동 실행
- Scope: Backend ECS Service 우선 배포
- Health Check: 고정 DNS가 아니라 `bada-dev-alb` 이름으로 ALB DNS를 조회한 뒤 `/health` 확인
- Terraform은 ECS Service 골격을 관리하고, 배포 후 task definition revision 변경은 GitHub Actions가 관리한다. 따라서 ECS Service의 `task_definition` drift는 Terraform에서 무시한다.

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
- 실행 브랜치: `develop`
- 입력값 예시: `bada-dev-backend:9` 또는 Task Definition ARN
- 사용 시점: 새 배포 후 `/health` 실패, 주요 API 장애, CloudWatch 로그에서 기동 오류가 확인될 때
- 주의: 롤백은 ECS Service가 참조하는 Task Definition revision만 되돌린다. DB migration, S3 데이터, Secrets 값 변경은 자동으로 되돌리지 않는다.

자동배포 검증 결과:

```text
PR #24 merge 이후 develop push 기준 실행 성공
CI workflow     : success
Deploy workflow : success
Backend task def: bada-dev-backend:9
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

- 기본값: `alarm_actions = []`
- 의미: 알람 객체는 생성하되 SNS 이메일/Slack 알림은 아직 연결하지 않는다.
- 확장: 알림이 필요하면 SNS Topic ARN을 `alarm_actions`에 추가한다.
- 적용 결과: `terraform apply`로 8개 알람 생성 완료, 이후 `terraform plan` 기준 `No changes` 확인
- 참고: 생성 직후에는 CloudWatch metric 데이터가 충분하지 않아 `INSUFFICIENT_DATA`로 보일 수 있다.

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
