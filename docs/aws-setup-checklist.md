# AWS 인프라 셋업 및 운영 체크리스트

> BADA 팀 공용 AWS 인프라 준비 상태를 확인하는 문서다.
> 초기 환경 설정, 현재 완료된 인프라, 남은 운영 작업을 한곳에서 추적한다.

## 운영 기준

| 항목 | 기준 |
| --- | --- |
| 프로젝트 운영 기간 | `2026-06-04 ~ 2026-07-10` |
| 팀 전체 AWS 예산 | `1,500달러` |
| 기본 리전 | `ap-northeast-2` 서울 |
| 기준 브랜치 | `develop` |
| IaC 도구 | Terraform |
| 배포 대상 | ECS Fargate |

## 핵심 운영 원칙

- [x] 팀 공용 AWS 계정을 기준으로 리소스를 관리한다.
- [x] Terraform으로 관리하는 리소스는 콘솔에서 직접 수정하지 않는다.
- [x] 실제 `terraform apply`는 인프라 담당자가 수행한다.
- [x] 팀원은 AWS 콘솔 조회, `terraform plan`, RDS 접속, 로그 확인 중심으로 사용한다.
- [x] `terraform.tfvars`는 로컬 전용 파일이며 GitHub에 커밋하지 않는다.
- [x] 민감정보는 Secrets Manager, 비민감 설정은 SSM Parameter Store로 분리한다.
- [x] 인프라 비용 절감을 위해 NAT Gateway는 사용하지 않는다.
- [x] RDS는 private subnet + Single-AZ 기준으로 운영한다.
- [x] Backend task를 계속 실행하면 Fargate 비용이 발생하므로 필요 시 `desired_count`를 조정한다.

## 계정 / 권한 / 비용

- [x] 팀 공용 AWS 계정 사용 기준 정리
- [x] 팀원 IAM User 생성
- [x] 팀원별 콘솔 로그인 및 비밀번호 변경
- [x] 팀원 Access Key 발급 및 AWS CLI 설정 가능 상태 확인
- [x] 팀원 IAM 권한 보강
- [x] 리전 `ap-northeast-2` 고정
- [x] AWS Budgets 비용 알림 생성
- [x] 팀 전체 예산 `1,500달러` 기준 공유

## Terraform / 네트워크

- [x] Terraform 초기화: `cd infra && terraform init`
- [x] Terraform validate 통과
- [x] Terraform plan 기준 실제 AWS 리소스와 코드 일치 확인
- [x] VPC 생성
- [x] Public Subnet 2개 생성
- [x] Private Subnet 2개 생성
- [x] Internet Gateway 생성
- [x] Route Table 및 Subnet Association 구성
- [x] NAT Gateway 미사용 구조 확정
- [x] ALB / ECS는 public subnet 기준
- [x] RDS는 private subnet 기준

## 데이터 / 스토리지 / 큐

- [x] S3 Evidence Bucket 생성
- [x] S3 Report Bucket 생성
- [x] S3 Public Access Block 적용
- [x] S3 KMS 암호화 적용
- [x] KMS Key / Alias 생성
- [x] SQS Analysis Queue 생성
- [x] SQS Dead Letter Queue 생성
- [x] RDS PostgreSQL 생성
- [x] RDS private subnet 배치
- [x] RDS public access 비활성화
- [x] RDS Single-AZ 유지
- [x] RDS 삭제 보호 적용
- [x] RDS 자동 백업 7일 보존 적용
- [x] RDS 삭제 시 최종 스냅샷 생성 설정 적용
- [x] `bada` DB에 `postgis` extension 활성화
- [x] SSM Session Manager Port Forwarding으로 RDS 접속 검증

## 인증 / 설정 / Secret

- [x] Cognito User Pool 생성
- [x] Cognito App Client 생성
- [x] Secrets Manager에 앱 Secret 생성
- [x] Secret에 DB username/password 저장
- [x] Secret에 Backend용 `database_url` 저장
- [x] SSM Parameter Store에 비민감 설정값 저장
- [x] S3 bucket name, SQS queue URL, Cognito ID, AWS region을 SSM에 저장

## 컨테이너 / ECS / ALB

- [x] ECR Backend Repository 생성
- [x] ECR Worker Repository 생성
- [x] Backend Dockerfile 생성
- [x] Worker Dockerfile 생성
- [x] `.dockerignore` 생성
- [x] Backend Docker image 로컬 빌드 검증
- [x] Worker Docker image 로컬 빌드 검증
- [x] Backend Docker image ECR push 검증
- [x] Worker Docker image ECR push 검증
- [x] ECS Cluster 생성
- [x] ECS Task Execution Role 생성
- [x] ECS Task Role 생성
- [x] Backend Task Definition 생성
- [x] Worker Task Definition 생성
- [x] Backend ECS Service 생성
- [x] Worker ECS Service 생성
- [x] ALB 생성
- [x] Target Group 생성
- [x] ALB Listener를 Backend Target Group으로 연결
- [x] Backend Service `desired_count = 1` 수동 기동 검증
- [x] Worker Service는 SQS consumer 검증 전까지 `desired_count = 0` 유지
- [x] Target Group health `healthy` 확인
- [x] ALB `/health` 200 응답 확인
- [x] ALB `/version` 200 응답 확인

## 현재 수동 배포 검증 결과

```text
Backend ECR image : bada-dev-backend:latest
Worker ECR image  : bada-dev-worker:latest
Backend Service   : desired=1, running=1
Worker Service    : desired=0, running=0
Target Group      : healthy
ALB /health       : 200 {"status":"ok"}
ALB /version      : 200 {"name":"BADA","version":"0.1.0","auth_mode":"demo","storage_mode":"s3"}
```

## 남은 Infra / DevOps 작업

- [ ] GitHub Actions 배포 전략 확정
- [ ] GitHub Actions OIDC Provider 구성
- [ ] GitHub Actions용 IAM Role 생성
- [ ] GitHub Actions Role trust policy에 repo / branch 조건 설정
- [ ] ECR push 권한 최소화
- [ ] ECS deploy 권한 최소화
- [ ] `.github/workflows/deploy-dev.yml` 작성
- [ ] `develop` push 시 Backend image build / ECR push 자동화
- [ ] ECS Task Definition 새 revision 등록 자동화
- [ ] ECS Service update 자동화
- [ ] 배포 후 ALB `/health` 자동 검증
- [ ] 배포 실패 시 rollback 또는 이전 task definition 복구 절차 정리
- [ ] CloudWatch Alarm 세부화
- [ ] Well-Architected Tool 점검 및 milestone 저장

## 다른 파트 확인 필요 항목

### AI / Bedrock

- [ ] Bedrock Model access에서 사용할 Claude 모델 활성화 확인
- [ ] 사용할 Bedrock model ID 확정
- [ ] Backend/Worker에서 실제 Bedrock 호출 모드 전환 시점 결정
- [ ] AI 호출 비용 추적 기준 정리

### OCR / 외부 API

- [ ] Upstage Document Parse API 키 발급 여부 확인
- [ ] OCR API 키 보관 위치 확정
- [ ] 외부 API 호출 전 PII 마스킹 기준 확인

### PDF / 폰트

- [ ] Noto Sans KR 폰트 확보
- [ ] Khmer / Devanagari 폰트 확보
- [ ] Worker 컨테이너에 PDF 폰트 포함 여부 결정
- [ ] 다국어 PDF 렌더링 육안 검증

## 명령어

### AWS 계정 확인

```bash
aws sts get-caller-identity
```

### Terraform 상태 확인

```bash
cd infra
terraform validate
terraform plan -var-file="terraform.tfvars"
```

### Backend 배포 상태 확인

```bash
aws ecs describe-services \
  --region ap-northeast-2 \
  --cluster bada-dev-cluster \
  --services bada-dev-backend bada-dev-worker
```

### ALB health check

```bash
curl http://bada-dev-alb-1367676989.ap-northeast-2.elb.amazonaws.com/health
curl http://bada-dev-alb-1367676989.ap-northeast-2.elb.amazonaws.com/version
```

## 주의사항

- `terraform.tfvars`에는 실제 DB 비밀번호가 들어갈 수 있으므로 절대 커밋하지 않는다.
- ECR image tag를 만들 때 shell 변수는 `"${REPO}:latest"`처럼 중괄호로 감싼다.
- Backend task 1개가 실행 중이면 Fargate 비용이 발생한다.
- 검증 종료 후 비용을 줄여야 하면 인프라 담당자가 `backend_desired_count = 0`으로 되돌리고 Terraform apply를 수행한다.
- Worker는 아직 장기 실행 SQS consumer 검증 전이므로 기본적으로 실행하지 않는다.
