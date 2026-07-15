# BADA 프로젝트 종료·데이터 보존 런북

> 목표 종료일: 2026-07-10
> 대상: BADA dev AWS 환경
> 원칙: 민감한 증거 데이터는 목적 달성 후 불필요하게 보존하지 않는다.

## 1. 권고 정책

### 데이터

- 실사용자·인터뷰 참여자·팀원의 개인정보가 포함된 Evidence, Report, RDS 데이터는 프로젝트 종료 후 삭제한다.
- 발표 재현에 필요한 자료는 개인정보가 없는 합성 데이터만 별도 보존한다.
- 실데이터가 들어 있는 RDS 최종 snapshot은 기본적으로 장기 보존하지 않는다.
- 복구 필요성이 승인된 경우에만 전용 KMS Key로 암호화한 snapshot을 기간과 삭제 책임자를 지정해 보존한다.
- ALB access log는 기존 30일 lifecycle을 유지한다.

### 인프라

- RDS 암호화 마이그레이션은 남은 dev 운영 기간에 강행하지 않는다.
- 운영·재사용 환경으로 전환할 때는 암호화 신규 RDS로 복원·전환한다.
- Backend·Worker Task Role 분리는 현재 dev 환경에서는 이월하고 운영 전 필수 항목으로 지정한다.
- CloudFront, VPC **Interface** Endpoint(SQS/ECR)는 MVP 종료 환경에 추가하지 않는다. (NAT Gateway는 2026-07-03 적용됨 → 아래 토글로 정리)
- WAF·ECS Auto Scaling·GuardDuty/Security Hub·Worker Fargate Spot·S3 **Gateway** Endpoint·**ECS Private Subnet+NAT Gateway(2026-07-03)**는 이미 적용됨 → 종료 시 각 토글(`security_monitoring_enabled`, `backend/worker_autoscaling_enabled`, `worker_fargate_spot_enabled`, `s3_gateway_endpoint_enabled`, `s3_lifecycle_enabled`, `ecs_in_private_subnets`, `nat_gateway_enabled`)을 false로 되돌려 정리한다. NAT/EIP 과금 정지를 위해 `nat_gateway_enabled=false`가 특히 중요하다.
- **Cognito 레거시 정리**: 앱은 소셜 OAuth를 쓰므로 Cognito는 미사용이다. 종료 시 `data.tf`의 Cognito User Pool/Client/Domain(+ Google IdP)과 SSM `cognito/*` 파라미터, `compute.tf` 백엔드 태스크의 `COGNITO_*` 환경변수를 제거한다(운영 전환 시에도 소셜 OAuth 유지 방침이면 코드에서 삭제 권장).
- **레거시 디렉토리**: `frontend/`(Next.js, `frontend_enabled=false`로 배포 제외)와 `mobile/`(초기 Capacitor 앱)은 미운영이다. 리포 정리 시 보존/삭제를 결정한다(인프라 비용과는 무관).

위 정책은 인프라 권고안이며, 데이터 보존·삭제와 snapshot 보존은 PM·팀의 최종 승인을 받아 실행한다.

## 2. 종료 전 확인

- [ ] 팀 기능 E2E와 데모 완료
- [ ] 보존할 합성 데이터 목록 확정
- [ ] Evidence·Report·RDS에 실데이터가 있는지 분류
- [ ] RDS snapshot 보존 여부와 보존 기간 승인
- [ ] GitHub Actions 자동배포 중지 시점 공지
- [ ] 종료 담당자와 검증 담당자 지정

## 3. 종료 순서

### 3.1 쓰기와 배포 중지

1. 팀에 서비스 종료 시간 공지
2. 앱(모바일)에서 신규 업로드 중지 (웹 프론트는 이미 배포 제외)
3. GitHub Actions 자동 배포가 다시 서비스를 기동하지 않도록 branch 운영 중지
4. SQS Main Queue와 DLQ가 0인지 확인

### 3.2 데이터 처리

1. 합성 데모 자료만 별도 보존
2. Evidence·Report S3 객체 목록과 DB 데이터 확인
3. 승인된 정책에 따라 실데이터 삭제
4. snapshot 보존이 승인됐다면 암호화 snapshot 생성 및 만료일 기록

S3 확인:

```bash
aws s3 ls s3://bada-dev-evidence/ --recursive
aws s3 ls s3://bada-dev-report/ --recursive
```

버킷을 비우기 전 객체 버전 사용 여부도 확인한다.

```bash
aws s3api get-bucket-versioning --bucket bada-dev-evidence
aws s3api get-bucket-versioning --bucket bada-dev-report
```

### 3.3 애플리케이션 중지

다음 ECS Service를 `desired_count=0`으로 낮춘다.

```text
bada-dev-backend
bada-dev-worker
bada-dev-prometheus
bada-dev-grafana
```
> 웹 프론트(`bada-dev-frontend`)는 `frontend_enabled=false`로 이미 미배포 — 대상 아님.

Terraform 변수 또는 코드로 변경하고 plan에서 의도한 scale-down만 발생하는지 확인한 뒤 적용한다.

### 3.4 고정비 리소스 종료

권장 순서:

```text
Grafana/Prometheus
→ Backend/Worker ECS
→ EFS
→ SSM DB 접근 EC2
→ RDS
→ ALB·Target Group·Route 53 필요 레코드
→ ECS Cluster·Security Group·VPC
```

S3, KMS Key, CloudWatch Logs와 snapshot은 데이터 보존 결정 이후 마지막에 처리한다.

## 4. RDS 종료

1. 삭제 보호 해제
2. 최종 snapshot 정책 확인
3. 실데이터가 있는 경우 불필요한 평문 snapshot을 남기지 않음
4. 승인된 암호화 snapshot이 있으면 ARN·KMS Key·삭제일 기록
5. RDS 삭제
6. Secrets Manager의 DB endpoint와 credential 삭제 또는 비활성화

Terraform의 현재 기본값은 최종 snapshot을 생성하도록 되어 있다. 실제 종료 전에 데이터 분류 결과에 따라 `db_skip_final_snapshot`과 snapshot 정책을 명시적으로 결정한다.

## 5. 종료 후 검증

- ECS running task 0
- RDS·ALB·EFS·SSM 접근 EC2가 종료 또는 승인된 보존 상태
- Cognito User Pool/Client/Domain·SSM `cognito/*`·백엔드 `COGNITO_*` env 제거 확인(레거시)
- Main Queue와 DLQ 0
- Evidence·Report에 승인되지 않은 객체 없음
- Route 53에 불필요한 서비스 레코드 없음
- CloudWatch에 반복 재기동·배포 없음
- Cost Explorer에서 다음 날부터 고정비 감소 확인
- 남은 snapshot·S3·KMS·Route 53·도메인의 예상 월 비용 기록

## 6. 보존 자산 기록

| 자산 | 기본 결정 | 승인자 | 삭제 예정일 |
| --- | --- | --- | --- |
| Evidence S3 실데이터 | 삭제 | 팀 승인 필요 | 2026-07-10 |
| Report S3 실데이터 | 삭제 | 팀 승인 필요 | 2026-07-10 |
| 합성 데모 데이터 | 필요 최소한 보존 | PM | 별도 결정 |
| RDS snapshot | 기본 미보존, 필요 시 암호화·기한부 보존 | 팀 승인 필요 | 별도 결정 |
| ALB Log | 30일 lifecycle | 인프라 | 자동 |
| CloudWatch Log | 14일 retention | 인프라 | 자동 |
| Route 53 도메인 | 팀 자산으로 유지 여부 결정 | PM | 별도 결정 |
