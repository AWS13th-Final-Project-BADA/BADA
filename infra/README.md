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
- 프로젝트 운영 기간은 `2026-06-04 ~ 2026-07-10`, 팀 전체 AWS 총 예산은 `1,500달러`
