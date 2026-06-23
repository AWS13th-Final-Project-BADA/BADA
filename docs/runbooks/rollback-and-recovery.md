# BADA ECS 롤백·복구 런북

> 대상 환경: `ap-northeast-2`, ECS Cluster `bada-dev-cluster`
> 이 문서는 컨테이너 Task Definition 롤백 절차를 다룬다. DB migration, 데이터, Secret, Terraform 변경은 별도 복구가 필요하다.
> 기준일: 2026-06-24

## 1. 현재 실행 상태와 롤백 후보

| 서비스 | 현재 실행 | ACTIVE 후보 예시 | 자동 rollback | 수동 경로 |
| --- | --- | --- | --- | --- |
| Backend | `bada-dev-backend:41` | `:40` | 활성 | GitHub Actions workflow |
| Worker | `bada-dev-worker:17` | `:14` | 활성 | ECS CLI |
| Frontend | `bada-dev-frontend:3` | `:2` | 활성 | ECS CLI |
| Prometheus | `bada-dev-prometheus:2` | `:1` | 미활성 | ECS CLI |
| Grafana | `bada-dev-grafana:1` | 이전 revision 없음 | 미활성 | 현재 revision 재배포 |

후보 revision은 AWS에서 `ACTIVE`임을 확인한 예시다. 실제 롤백 직전에는 최신 revision 목록, image tag, 변경 이력과 DB 호환성을 다시 확인한다.

## 2. 롤백 전 확인

```bash
REGION=ap-northeast-2
CLUSTER=bada-dev-cluster

for family in bada-dev-backend bada-dev-worker bada-dev-frontend; do
  aws ecs list-task-definitions \
    --region "$REGION" \
    --family-prefix "$family" \
    --status ACTIVE \
    --sort DESC \
    --max-items 5 \
    --query 'taskDefinitionArns' \
    --output text | tr '\t' '\n'
done

aws ecs describe-services \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --services bada-dev-backend bada-dev-worker bada-dev-frontend \
  --query 'services[].{service:serviceName,taskDefinition:taskDefinition,rollout:deployments[0].rolloutState}' \
  --output table
```

선택한 후보의 image와 상태도 확인한다.

```bash
aws ecs describe-task-definition \
  --region "$REGION" \
  --task-definition <family:revision> \
  --query 'taskDefinition.{status:status,revision:revision,images:containerDefinitions[].image}'
```

## 3. Backend 수동 롤백

GitHub에서 다음 workflow를 실행한다.

```text
Actions
→ Rollback Dev Backend
→ Run workflow
→ task_definition에 확인한 family:revision 입력
```

Workflow: `.github/workflows/rollback-dev-backend.yml`

현재 workflow는 ALB HTTP URL을 검사한다. HTTP→HTTPS 301이 성공처럼 처리될 수 있으므로 workflow 완료 후 반드시 운영 HTTPS endpoint를 별도로 확인한다.

```bash
curl -fsS https://api.badasoft.com/health
```

## 4. Frontend·Worker·Prometheus ECS CLI 롤백

```bash
REGION=ap-northeast-2
CLUSTER=bada-dev-cluster
SERVICE=<service-name>
TARGET=<family:revision>

aws ecs update-service \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$TARGET"

aws ecs wait services-stable \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --services "$SERVICE"

aws ecs describe-services \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query 'services[0].{desired:desiredCount,running:runningCount,rollout:deployments[0].rolloutState,taskDefinition:taskDefinition}'
```

롤백 후 검증:

| 서비스 | 검증 |
| --- | --- |
| Frontend | `https://badasoft.com/api/health` 200 |
| Worker | consumer 시작 로그, 테스트 메시지 처리, SQS/DLQ 정상 |
| Prometheus | Grafana에서 Prometheus와 Backend target `UP` |

Worker는 ALB target이 없으므로 Queue가 0이라는 사실만으로 완료하지 않는다. consumer 로그와 실제 테스트 메시지 처리를 함께 확인한다.

## 5. 컨테이너 롤백으로 복구되지 않는 변경

- Alembic DB migration과 스키마 변경
- 처리 완료된 사건, 분석 결과 등 데이터 변경
- Secrets Manager와 SSM Parameter 값
- Terraform 리소스와 네트워크 변경

위 변경이 포함됐다면 코드 rollback 전에 별도의 복구·호환성 계획을 세운다.

## 6. 완료 기준

```text
Task Definition 후보 재확인
→ ECS update
→ Service stable
→ 서비스별 health·로그·메시지 처리 확인
→ Alarm·SQS/DLQ 정상 확인
→ 적용 revision과 결과 기록
```
