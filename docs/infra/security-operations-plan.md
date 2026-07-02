# BADA 인프라 보안·운영 결정 계획

> 기준일: 2026-06-24
> 실제 AWS 조회 결과를 바탕으로 Week 3에 적용할 항목과 팀 승인이 필요한 항목을 구분한다.

## 1. ECR 이미지 보안

| 이미지 | Manifest | 최신 Scan | 판정 |
| --- | --- | --- | --- |
| Frontend | Docker v2 | Critical 1 / High 8 / Medium 4 / Low 2 | 담당자 수정 또는 MVP 위험 수용 필요 |
| Backend | Docker v2 | Critical 1 / High 3 / Medium 2 | 담당자 수정 또는 MVP 위험 수용 필요 |
| Worker | OCI image index | Scan 없음 | 다음 CD에서 scan-compatible manifest 필요 |

현재 발견 건수는 base image와 OS package를 포함한다. CVE 개수만으로 앱 취약성을 확정하지 않고 사용 경로, 수정 버전과 base image 업데이트 가능성을 함께 확인한다.

다음 작업:

1. Frontend·Backend 담당자에게 Critical/High 목록 전달
2. Docker base image와 package lock 업데이트 검토
3. 재빌드 후 ECR Scan 비교
4. Worker workflow에 `--provenance=false` 적용 여부와 실제 manifest 확인
5. 수정 불가 항목은 위험 수용자·이유·운영 전 완료 시점을 기록

## 2. Backend·Worker Task Role 분리안

현재 Backend와 Worker는 `bada-dev-ecs-task-role` 하나를 공유한다. Frontend에는 Application Task Role이 없다.

제안:

```text
bada-dev-backend-task-role
  - Evidence S3와 필요한 KMS 작업
  - SQS SendMessage 중심
  - Backend가 실제 호출하는 Bedrock·Transcribe·Translate
  - DB Secret과 필요한 SSM Parameter

bada-dev-worker-task-role
  - Evidence·Report S3와 KMS
  - SQS ReceiveMessage/DeleteMessage/ChangeMessageVisibility
  - Worker Bedrock·Transcribe·Translate
  - DB Secret과 필요한 SSM Parameter
```

분리 전에는 코드와 CloudTrail을 기준으로 실제 API를 확인한다. 특히 Backend inline transcription과 AI Chat 사용 여부에 따라 AWS AI 권한이 달라질 수 있다.

적용 순서:

1. Terraform으로 Role 2개와 정책 생성
2. Task Definition의 `task_role_arn`만 서비스별 Role로 변경
3. `plan`에서 IAM·Task Definition 변경만 발생하는지 확인
4. Backend health와 인증·업로드·SQS 발행 검증
5. Worker 분석·STT·PDF와 DLQ 검증
6. 안정화 후 공용 Role 제거

Week 3 즉시 적용 여부는 팀 E2E 일정과 함께 결정한다. 검증 없이 공용 Role을 제거하지 않는다.

## 3. 비용·Budget

| 항목 | 현재 값 |
| --- | ---: |
| 팀 합의 총상한 | `$1,500` |
| AWS Budget | `$1,000 / month` |
| Actual | `$55.324` |
| Forecast | `$74.62` |

주요 누적 비용:

| 서비스 | 비용(USD) |
| --- | ---: |
| RDS | 9.46 |
| ELB | 7.51 |
| VPC | 5.78 |
| EC2 Compute | 4.25 |
| ECS | 2.83 |
| Claude Sonnet 4.6 | 2.98 |
| Amazon Registrar | 15.00 |

Budget 알림은 Actual 5/50/80/90/100%, Forecast 80/100% 기준으로 구성돼 있다. Actual 5% 알림만 현재 ALARM이며 총예산과 Forecast에는 충분한 여유가 있다.

운영 판단:

- 7월 10일까지는 RDS·ALB·VPC 고정비를 매일 또는 주요 배포 후 확인한다.
- Bedrock 모델 테스트는 팀원이 model ID와 테스트 건수를 기록한다.
- `$1,500`은 팀 프로젝트 전체 상한, `$1,000`은 월 AWS 경보 기준으로 구분한다.
- 프로젝트 종료 계획에서 RDS·ALB·EFS·ECS·SSM 접근 EC2 종료 순서를 명시한다.

비용 귀속 태그:

- 주요 ECS Service, RDS, Evidence/Report/ALB Log S3에 `Project=bada`, `Environment=dev`, `ManagedBy=terraform`이 적용돼 있다.
- Cost Explorer의 Cost Allocation Tag 활성 상태는 결제 관리 계정 권한이 필요해 현재 연결 계정에서 조회할 수 없었다.
- 결제 관리자에게 세 태그의 활성화 여부를 확인하고, 비활성이라면 Billing 콘솔에서 활성화한다.

## 4. 현재 결정 대기

- RDS 암호화 마이그레이션 수행 시점
- Backend·Worker Task Role 즉시 분리 여부
- Frontend·Backend Critical 취약점의 수정 또는 위험 수용
- Worker scan-compatible 이미지 생성 시점
- Evidence·Report S3 보존 기간

## 5. 인프라 권고 결정

| 항목 | 권고 결정 | 완료 조건 |
| --- | --- | --- |
| RDS 암호화 | **완료 (2026-07-02)** — encrypted Multi-AZ DB로 cutover | — |
| Task Role 분리 | **완료 (PR #205)** — Backend/Worker 서비스별 최소권한 Role | — |
| Frontend·Backend CVE | 7/3 전 담당자 수정 또는 위험 수용 기록 | 재스캔 결과와 승인자 기록. 저위험 범프 완료(#B-3 부분), fastapi+starlette·weasyprint+pillow 메이저 잔여 |
| Worker Scan | 다음 Worker CD에서 manifest와 scan 재확인 | Docker v2 또는 scan 가능한 이미지 결과 |
| Evidence·Report | 데모 중 자동 만료 미적용, 종료 시 실데이터 삭제 | PM 승인과 종료 런북 실행. 비용 계층 전환 Lifecycle은 적용 완료(#B-5) |
| Auto Scaling | **완료 (#4, PR #203)** — Backend CPU + Worker SQS backlog, min=1/max=3 | k6 부하 검증 완료(#9) |
| WAF·CloudFront·VPC Endpoint | WAF **완료**(#7), S3 Gateway Endpoint **완료**(2026-07-02). CloudFront·Interface Endpoint는 미적용 | 외부 공개 운영 전 재검토 |

종료·데이터 보존 절차는 `docs/runbooks/project-closure.md`를 기준으로 한다.
