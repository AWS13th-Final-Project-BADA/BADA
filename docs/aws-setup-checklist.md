# AWS 셋업 체크리스트

> 인프라 코드 적용 전후에 필요한 공용 AWS 준비 작업을 정리한 문서다.
> 운영 기준: `2026-06-04 ~ 2026-07-10`, 팀 전체 AWS 총 예산 `1,500달러`

## 1. 사전 준비

### 계정·권한
- [ ] 팀 공용 AWS 계정/조직 확인, IAM 사용자·역할 생성 (최소권한)
- [ ] 리전 고정: **ap-northeast-2 (서울)**
- [ ] 비용 알람: Budgets로 월 한도 + 80% 알림 (CloudWatch)
- [ ] 예산 운영 원칙 공유: AI 비용도 포함한 총액 1,500달러 기준, 인프라는 `NAT Gateway 미사용`, `RDS Single-AZ`, `Fargate 최소 안정 사양`

### Bedrock
- [ ] 콘솔 → Bedrock → **Model access**에서 Claude 모델 활성화 신청/승인
- [ ] 사용할 모델 ID 확정 후 `.env`의 `BEDROCK_MODEL_ID` 갱신
- [ ] Vision 호출 리전이 모델 지원 리전인지 확인

### Upstage
- [ ] Document Parse API 키 발급 → `.env` `UPSTAGE_API_KEY`
- [ ] ⚠️ 전송 전 PII 마스킹 적용 확인 (security.md)

## 2. Terraform 적용 전 점검

- [ ] `cd infra && terraform init`
- [ ] `terraform.tfvars` 작성 (`db_password`, 환경명, CIDR, 이미지 URI 등)
- [ ] `.env.example`와 Terraform outputs를 어떻게 매핑할지 팀 내 합의
- [ ] VPC / subnet 전략 재확인: `ALB/ECS public`, `RDS private`
- [ ] NAT Gateway를 생성하지 않는 구조인지 확인
- [ ] RDS는 `Single-AZ` 기준인지 확인

## 3. Terraform apply 후 확인

- [ ] Terraform 초기화: `cd infra && terraform init`
- [ ] S3 버킷(KMS 암호화, 퍼블릭 차단) — Terraform으로 생성
- [ ] RDS PostgreSQL 생성 후 `CREATE EXTENSION postgis;` 적용 경로 확인
- [ ] SQS 큐 생성, URL을 `.env` `SQS_QUEUE_URL` 또는 런타임 설정값에 반영
- [ ] SQS DLQ 생성 여부 확인
- [ ] ECR 리포지토리 생성 (backend / worker)
- [ ] Cognito User Pool + App Client 생성 → `.env` 갱신
- [ ] 민감정보는 Secrets Manager, 비민감 설정은 SSM Parameter Store로 분리
- [ ] CloudWatch 로그 보존기간은 7일 또는 14일로 설정

## 4. 애플리케이션 AWS 전환 체크

- [ ] `DATABASE_URL`을 RDS 기준으로 교체
- [ ] `STORAGE_MODE=s3` 전환
- [ ] `AUTH_MODE=cognito` 전환
- [ ] `SQS_QUEUE_URL`, `COGNITO_*`, `AWS_REGION` 반영
- [ ] backend / worker가 AWS 리소스를 읽을 수 있도록 환경변수 또는 런타임 주입 경로 확정

## 5. 다음 단계 구현 항목

- [ ] ALB와 ECS backend service 실제 연결
- [ ] ECS backend / worker task definition 작성
- [ ] ECS backend / worker service 작성
- [ ] Secrets / SSM 런타임 주입
- [ ] CloudWatch Alarm 구체화
- [ ] GitHub Actions 기반 ECR/ECS 배포 자동화

## 6. 폰트 (PDF — W3 전에)

- [ ] Noto Sans KR / Khmer / Devanagari .ttf 확보 → worker 컨테이너에 임베딩
- [ ] 크메르·데바나가리 1장 렌더 육안 검증
