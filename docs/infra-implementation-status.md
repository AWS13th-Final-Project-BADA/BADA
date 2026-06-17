# BADA 인프라 구현 현황

> 팀 공용 AWS 계정에 현재 구현된 BADA 인프라 상태를 한눈에 확인하기 위한 문서다.
> 실행 방법이나 상세 의사결정이 아니라, “무엇이 구축되어 있고 현재 어떤 상태인지”만 기록한다.

## 1. 전체 요약

| 항목 | 현재 상태 |
| --- | --- |
| AWS Region | `ap-northeast-2` |
| IaC | Terraform |
| 배포 대상 | ECS Fargate |
| 기준 브랜치 | `develop` |
| Backend 상태 | ECS Service 실행 중 |
| Worker 상태 | SQS consumer 구현 전으로 미실행, 배포 workflow 코드 준비 |
| DB | RDS PostgreSQL, private subnet |
| 파일 저장소 | S3 Evidence / Report Bucket |
| 비밀값 관리 | Secrets Manager |
| 설정값 관리 | SSM Parameter Store |
| 배포 자동화 | Backend 자동배포 완료, Worker 자동배포 workflow 코드 및 AWS 권한 반영 완료 |
| 롤백 | GitHub Actions 수동 롤백 workflow |
| 모니터링 | CloudWatch Logs / Alarms |
| Well-Architected | Workload 생성 및 초기 milestone 저장 완료 |

## 2. 현재 실행 상태

| 구분 | 상태 |
| --- | --- |
| Backend ECS Service | `desired=1`, `running=1` |
| Worker ECS Service | `desired=0`, `running=0` |
| Backend Task Definition | `bada-dev-backend:9` |
| Worker Task Definition | `bada-dev-worker:2` |
| Target Group | `healthy` |
| ALB `/health` | `200 {"status":"ok"}` |
| ALB `/version` | `200 {"name":"BADA","version":"0.1.0","auth_mode":"demo","storage_mode":"s3"}` |

## 3. 아키텍처 흐름

```text
Users
  -> ALB
  -> ECS Fargate Backend
  -> RDS PostgreSQL / S3 / SQS / Cognito / Secrets Manager / SSM / CloudWatch

SQS
  -> ECS Fargate Worker
  -> AI / OCR / Translation
  -> RDS PostgreSQL / S3
```

현재 Worker는 인프라만 준비되어 있으며, 장기 실행 SQS consumer 구현 전까지 실행하지 않는다.

## 4. 리소스 구현 현황

### Network

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| VPC | 완료 | BADA dev 인프라 기본 네트워크 |
| Public Subnet 2개 | 완료 | ALB / ECS 배치 |
| Private Subnet 2개 | 완료 | RDS 배치 |
| Internet Gateway | 완료 | Public subnet 외부 통신 |
| Route Table / Association | 완료 | Public / Private routing 분리 |
| NAT Gateway | 미사용 | 비용 절감을 위해 MVP 단계 제외 |

### Compute / Container

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| ECS Cluster | 완료 | Backend / Worker 공용 |
| Backend Task Definition | 완료 | GitHub Actions 배포 기준 최신 revision 사용 |
| Worker Task Definition | 완료 | Worker consumer 구현 후 기동 예정 |
| Backend ECS Service | 실행 중 | `desired_count=1` |
| Worker ECS Service | 대기 | `desired_count=0` |
| Backend ECR Repository | 완료 | Backend image 저장 |
| Worker ECR Repository | 완료 | Worker image 저장 |
| ALB | 완료 | Backend 진입점 |
| Target Group | 완료 | Backend health check 연결 |

### Data / Storage / Queue

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| RDS PostgreSQL | 완료 | Single-AZ, private subnet |
| RDS Deletion Protection | 완료 | 실수 삭제 방지 |
| RDS Automated Backup | 완료 | 7일 보존 |
| RDS Final Snapshot | 완료 | 삭제 시 최종 스냅샷 생성 |
| PostGIS Extension | 완료 | GPS 위치 데이터 확장 대비 |
| S3 Evidence Bucket | 완료 | 증거 파일 저장 |
| S3 Report Bucket | 완료 | 생성 리포트 저장 |
| S3 SSE-KMS | 완료 | 버킷 암호화 |
| SQS Analysis Queue | 완료 | 비동기 분석 작업 큐 |
| SQS DLQ | 완료 | 실패 메시지 격리 |

### Auth / Config / Secret

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| Cognito User Pool | 완료 | 사용자 인증 기반 |
| Cognito App Client | 완료 | 앱 클라이언트 |
| Secrets Manager | 완료 | DB 접속 정보와 앱 secret |
| SSM Parameter Store | 완료 | S3, SQS, Cognito, Region 등 비민감 설정 |
| IAM User / Role | 완료 | 팀원 접근 및 GitHub Actions 배포 역할 |

### Observability / Cost

| 리소스 | 상태 | 비고 |
| --- | --- | --- |
| CloudWatch Log Group | 완료 | Backend / Worker 로그 |
| CloudWatch Alarm | 완료 | ALB, ECS, RDS, SQS 핵심 지표 8개 |
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
| 현재 실행 상태 | `desired_count=0` 유지 |
| AWS 권한 반영 | 완료. Deploy Role이 Backend / Worker ECR push 가능 |
| 실행 검증 | 대기. `worker/**` 변경 push 또는 workflow default branch 반영 후 검증 |

Worker는 아직 SQS long-running consumer가 구현되지 않았으므로, 배포 workflow는 이미지와 Task Definition revision을 갱신하는 용도로만 사용한다. Worker consumer가 완성되면 Terraform에서 `worker_desired_count`를 올려 실제 실행 상태로 전환한다.

검증 기록:

```text
terraform apply : success
changed         : 1 IAM role policy
terraform plan  : No changes
Worker service  : desired=0, running=0
```

주의: 현재 GitHub 기본 브랜치가 `main`이므로, `develop`에만 존재하는 신규 workflow는 GitHub Actions 수동 실행 목록에 바로 노출되지 않을 수 있다. Worker workflow 실제 실행 검증은 `worker/**` 변경이 `develop`에 push될 때 자동 실행되거나, workflow가 default branch에 반영된 뒤 수동 실행으로 진행한다.

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

## 6. 현재 미구현 / 대기 항목

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| Worker SQS long-running consumer | 미구현 | 구현 후 Worker Service 기동 필요 |
| Worker 자동배포 실행 검증 | 대기 | `worker/**` 변경 push 또는 workflow default branch 반영 후 가능 |
| Well-Architected 1차 답변 | 완료 | 57개 질문 답변 및 milestone #2 저장 |
| SNS 기반 알림 전송 | 대기 | 현재 CloudWatch Alarm은 알람 객체만 생성 |

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
| P0 | ALB HTTPS/ACM 적용 및 HTTP -> HTTPS redirect 검토 | Security | 대기 |
| P0 | CloudWatch Alarm에 SNS 이메일 또는 Slack 알림 연결 | Operational Excellence / Reliability | 대기 |
| P0 | Worker SQS consumer 구현 후 Worker Service 기동 검증 | Reliability / Cost | 개발 대기 |
| P1 | RTO/RPO와 RDS restore rehearsal 절차 정의 | Reliability | 대기 |
| P1 | ECR image scan, dependency scan, CI 보안 검증 강화 | Security | 대기 |
| P1 | ECS Backend/Worker Auto Scaling과 부하 테스트 기준 수립 | Performance / Reliability | 대기 |
| P2 | Cost allocation tag, Cost Explorer/CUR 기반 비용 분석 강화 | Cost Optimization | 대기 |
| P2 | S3 lifecycle/retention 정책과 데이터 분류 기준 구체화 | Security / Sustainability | 대기 |

## 8. 참고 문서

| 문서 | 목적 |
| --- | --- |
| `infra/README.md` | Terraform 실행 방법과 인프라 코드 구조 |
| `docs/OWNERSHIP.md` | 파트별 담당 영역 |
| `.github/workflows/deploy-dev.yml` | Backend 자동배포 workflow |
| `.github/workflows/deploy-dev-worker.yml` | Worker 자동배포 workflow |
| `.github/workflows/rollback-dev-backend.yml` | Backend 수동 롤백 workflow |
