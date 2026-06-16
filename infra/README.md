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
- 프로젝트 운영 기간은 `2026-06-04 ~ 2026-07-10`, 팀 전체 AWS 총 예산은 `1,500달러`

수동 배포 검증 결과:

```text
Backend ECS Service: desired=1, running=1
Worker ECS Service : desired=0, running=0
ALB /health        : 200 {"status":"ok"}
ALB /version       : 200 {"name":"BADA","version":"0.1.0","auth_mode":"demo","storage_mode":"s3"}
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

자동배포 검증 결과:

```text
PR #19 merge 이후 develop push 기준 실행 성공
CI workflow     : success
Deploy workflow : success
Backend task def: bada-dev-backend:3
ECS state       : desired=1, running=1, rolloutState=COMPLETED
ALB /health     : 200 {"status":"ok"}
```

주의: `terraform.tfvars`는 로컬 전용 파일이며 GitHub에 커밋하지 않는다. Backend task를 계속 실행하면 Fargate 비용이 발생하므로 검증 종료 후 필요 시 `backend_desired_count = 0`으로 되돌린다.
