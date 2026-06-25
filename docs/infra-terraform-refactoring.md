# Terraform 구조 리팩터링 — 서비스별 State 분리

## 배경

초기에는 빠른 구축을 위해 `main.tf` 단일 파일(~1500줄)에 모든 인프라를 정의했다.
프로젝트가 안정화되면서 아래 문제가 드러났다:

- `terraform plan`만 해도 전체 리소스(80+)를 확인 → 느림
- monitoring 변경이 Backend CD를 트리거 (경로 기반 CI/CD)
- 한 리소스의 실수가 전체 인프라에 블라스트 반경

## 의사결정: 서비스별 분리

### 검토한 선택지

| 방식 | 설명 |
|------|------|
| A) 현행 유지 (단일 state) | main.tf + monitoring.tf, 하나의 `terraform apply`로 전체 관리 |
| B) 파일 분리만 (단일 state) | network.tf, ecs.tf 등 파일만 나눔. state는 하나 |
| C) 서비스별 state 분리 | 디렉토리별 독립 state. 서비스 간 참조는 remote_state 또는 SSM |

### 장단점 비교

| 기준 | A) 단일 state | B) 파일 분리 | C) 서비스별 분리 |
|------|--------------|-------------|-----------------|
| 구축 속도 | ✅ 빠름 | ✅ 빠름 | ❌ 초기 비용 |
| Plan/Apply 속도 | ❌ 전체 확인 | ❌ 동일 | ✅ 해당 서비스만 |
| 블라스트 반경 | ❌ 전체 | ❌ 전체 | ✅ 서비스 단위 |
| 팀 분업 | ❌ 충돌 가능 | △ 파일 단위 | ✅ 디렉토리 단위 |
| 참조 복잡도 | ✅ 직접 참조 | ✅ 직접 참조 | △ remote_state/SSM |
| 롤백 | ❌ 전체 | ❌ 전체 | ✅ 서비스 단위 |
| CI/CD 트리거 | ❌ 불필요한 배포 | ❌ 동일 | ✅ 정확한 범위 |

### 결정: C) 서비스별 분리

근거:
1. `terraform apply` 30분 소요 → 서비스별이면 3~5분으로 단축
2. monitoring 코드 변경이 Backend 재배포를 트리거하는 문제 해소
3. 인프라 담당 외 팀원도 자기 서비스 디렉토리만 파악하면 됨
4. 현업 표준 (AWS Well-Architected, HashiCorp 권장 패턴)

## 목표 구조

```
infra/
├── network/              # VPC, Subnet, Security Group, ALB, Route53, ACM
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf        # vpc_id, subnet_ids, alb_arn 등 → remote_state로 참조
│   └── backend.tf        # S3 state: bada/dev/network
│
├── database/             # RDS, Secrets Manager
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf        # db_endpoint, db_secret_arn
│   └── backend.tf        # S3 state: bada/dev/database
│
├── auth/                 # Cognito User Pool, Social IdP
│   ├── main.tf
│   └── backend.tf        # S3 state: bada/dev/auth
│
├── storage/              # S3 Buckets (evidence, report), SQS + DLQ
│   ├── main.tf
│   └── backend.tf        # S3 state: bada/dev/storage
│
├── backend/              # Backend ECS Service, Task Definition, ECR
│   ├── main.tf
│   └── backend.tf        # S3 state: bada/dev/backend
│
├── worker/               # Worker ECS Service, Task Definition, ECR
│   ├── main.tf
│   └── backend.tf        # S3 state: bada/dev/worker
│
├── frontend/             # Frontend ECS Service, Task Definition, ECR
│   ├── main.tf
│   └── backend.tf        # S3 state: bada/dev/frontend
│
├── monitoring/           # Prometheus, Grafana, EFS, CloudWatch Alarm, SNS
│   ├── main.tf
│   └── backend.tf        # S3 state: bada/dev/monitoring
│
└── shared/               # SSM Parameters, IAM 공통 Role, CloudWatch Log Groups
    ├── main.tf
    └── backend.tf        # S3 state: bada/dev/shared
```

## 서비스 간 참조 방식

```hcl
# backend/main.tf에서 network 참조
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "bada-tfstate-165749212250-ap-northeast-2"
    key    = "bada/dev/network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

resource "aws_ecs_service" "backend" {
  network_configuration {
    subnets = data.terraform_remote_state.network.outputs.public_subnet_ids
    # ...
  }
}
```

## 배포 순서 (의존성)

```
network → database → auth → storage → shared
                                         ↓
                              backend / worker / frontend / monitoring
```

## 마이그레이션 계획

1. 현재 state에서 `terraform state mv`로 리소스를 새 state로 이동
2. 또는 새 디렉토리에서 `terraform import`로 기존 리소스 가져오기
3. 서비스별 `terraform plan` → No changes 확인 (드리프트 없음)
4. CI/CD 워크플로우 paths 수정 (`infra/backend/**` → backend apply만)

## 리스크

| 리스크 | 대응 |
|--------|------|
| state 이동 중 실수로 리소스 삭제 | 반드시 plan 먼저 확인, state backup |
| remote_state 참조 순환 | 의존성 DAG 준수 |
| 팀원 혼란 | 마이그레이션 완료 후 기존 main.tf 제거, README 갱신 |
