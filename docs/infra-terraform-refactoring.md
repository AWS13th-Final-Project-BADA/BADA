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

## 적용 기준 (시점) — 프로덕션 전환 Phase 2 항목

> 이 리팩터링(서비스별 state 분리, 옵션 C)은 **MVP/dev 즉시 적용 항목이 아니다.**
> `docs/production-roadmap.md`의 Phase 2(고가용성 + 성능, "실 사용자 유입" 트리거)와 동일 시점에 검토한다.
> 인프라 담당(`infra/*.tf` 소유)이 시점과 방식을 확정한다.

### 적용을 시작할 조건 (아래 중 하나 이상 충족 시)

| 트리거 | 이유 |
|--------|------|
| 실 사용자 유입 / 프로덕션 전환 결정 | 블라스트 반경 축소·서비스별 롤백이 실가치를 가짐 |
| 인프라를 2명 이상이 상시 병렬 수정 | 디렉토리 단위 분업으로 머지 충돌면 축소 (단일 state에서는 충돌 빈발) |
| `terraform apply` 실측 시간이 운영에 부담 | 아래 "측정 선행" 결과가 기준치를 초과할 때 |
| 환경 분리(dev/stage/prod) 도입 | state 분리가 환경 분리의 전제가 됨 |

### 적용하지 않는 조건 (현재 BADA)

- 2026-07-10 유지 종료 예정인 MVP/dev → 마이그레이션 리스크(state mv/import 중 리소스 삭제) 대비 이득 없음
- 인프라 수정 빈도가 낮고 단일 담당이 관리 → 충돌면이 작음

### 측정 선행 (의사결정 전 보정 필요)

- 본문 "근거 1"의 `terraform apply 30분`은 **미검증 수치**다. 그 30분은 `deploy-dev.yml` job의 `timeout-minutes: 30`(백엔드 이미지 빌드/배포 한도)이며, 해당 CD는 terraform을 실행하지 않는다.
- 실제 `cd infra && time terraform apply`(또는 `plan`) 소요를 **1회 실측**해 본 수치로 교체한 뒤 분리 이득을 재평가한다. steady-state apply는 보통 수 분 수준일 가능성이 높다.

### 이미 적용한 경량 대체책 (state 분리 없이 동기 #2 해소)

문서가 지적한 "monitoring/인프라 변경이 Backend CD를 불필요하게 트리거" 문제는 **state 분리 없이 CI/CD 경로 수정으로 선해소**했다.

- `deploy-dev.yml`(Backend CD) 트리거 `paths`에서 `infra/*.tf`, `infra/terraform.tfvars.example` 제거.
- 효과: 인프라/모니터링 .tf 변경이 더 이상 Backend 이미지 재빌드·재배포를 유발하지 않는다.
- 근거: 해당 CD는 라이브 Task Definition의 컨테이너 이미지만 교체하고 terraform을 실행하지 않으므로, `.tf` 변경은 이 워크플로의 결과에 영향을 주지 않는다.

### 중간 단계 권고 (옵션 C 이전)

- **옵션 B(파일만 분리, state 유지)** 를 먼저 적용 가능: `main.tf`를 `network.tf`/`data.tf`/`ecs.tf`/`iam.tf`/`cognito.tf` 등으로 분리.
- state를 건드리지 않아 리스크가 거의 없고(파일 배치는 state와 무관), 병렬 작업 충돌면을 즉시 줄인다. 옵션 C는 그 이후 프로덕션 전환 시 검토.
