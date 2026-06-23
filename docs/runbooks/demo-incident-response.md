# BADA 데모 장애 대응 런북

> 데모 핵심 경로 `로그인 → 증거 업로드 → 분석 → Evidence Pack PDF`의 장애 위치를 빠르게 찾고 담당 영역을 구분한다.
> ECS rollback이 필요하면 `docs/runbooks/rollback-and-recovery.md`를 사용한다.
> 기준일: 2026-06-24

## 1. 공통 60초 점검

```bash
REGION=ap-northeast-2
CLUSTER=bada-dev-cluster

aws ecs describe-services \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --services bada-dev-backend bada-dev-worker bada-dev-frontend bada-dev-prometheus bada-dev-grafana \
  --query 'services[].{service:serviceName,desired:desiredCount,running:runningCount,rollout:deployments[0].rolloutState}' \
  --output table

aws cloudwatch describe-alarms \
  --region "$REGION" \
  --state-value ALARM \
  --query 'MetricAlarms[].AlarmName' \
  --output text

curl -fsS https://api.badasoft.com/health
curl -fsS https://badasoft.com/api/health
```

정상 기준:

- ECS 5개 서비스 `desired=running`, rollout `COMPLETED`
- 활성 CloudWatch Alarm 없음
- Main Queue와 DLQ에 비정상 잔여 메시지 없음
- Backend와 Frontend health 200

## 2. 로그인 장애

| 구분 | 확인 내용 |
| --- | --- |
| 경로 | Cognito Hosted UI·Google IdP → `api.badasoft.com` → Backend |
| Alarm | ALB Target 5xx, Unhealthy Target, Backend CPU·Memory |
| Logs | `/aws/ecs/bada-dev/backend`의 `auth`, `cognito`, `callback`, `JWT`, `401`, `403` |
| 주요 원인 | callback/logout URL, CORS, `AUTH_MODE`, JWKS 검증, Backend 장애 |
| 복구 | 설정 확인 또는 Backend rollback 후 HTTPS health 검증 |

실제 사용자 로그인 E2E가 완료되기 전까지 callback 이후 앱 복귀 문제는 인증·모바일 담당과 함께 판정한다.

## 3. 증거 업로드 장애

| 구분 | 확인 내용 |
| --- | --- |
| 경로 | Frontend·앱 → Backend presigned URL → Evidence S3 |
| Alarm | Frontend Unhealthy Target, Frontend CPU·Memory, ALB Target 5xx |
| Logs | `/aws/ecs/bada-dev/frontend`, `/aws/ecs/bada-dev/backend` |
| 주요 원인 | presigned URL 만료, S3·KMS 권한, Frontend 또는 Backend 장애 |
| 복구 | 서비스 rollback 또는 ECS Task Role의 S3·KMS 권한 점검 |

객체 저장과 암호화를 확인한다.

```bash
aws s3 ls s3://bada-dev-evidence/ --recursive | tail
aws s3api head-object --bucket bada-dev-evidence --key <object-key> \
  --query '{encryption:ServerSideEncryption,kmsKey:SSEKMSKeyId}'
```

## 4. 분석 장애

| 구분 | 확인 내용 |
| --- | --- |
| 경로 | Backend → SQS → Worker → Bedrock·Transcribe·Translate → RDS |
| Alarm | SQS Backlog·Oldest Message·DLQ, Worker CPU·Memory, RDS CPU·Storage |
| Logs | `/aws/ecs/bada-dev/worker`의 handler, `Traceback`, Bedrock, `AccessDenied` |
| 주요 원인 | Worker 중단, poison message, IAM, model ID, 외부 서비스 호출 실패 |
| 복구 | Worker rollback, 권한·model ID 수정, DLQ 메시지 원인 분석 |

```bash
aws sqs get-queue-attributes \
  --region ap-northeast-2 \
  --queue-url <analysis-queue-url> \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

aws sqs get-queue-attributes \
  --region ap-northeast-2 \
  --queue-url <dlq-url> \
  --attribute-names ApproximateNumberOfMessages
```

`infra_dlq_test` marker의 Traceback은 의도된 실패 경로 검증 로그일 수 있다. 메시지 본문과 발생 시각을 확인한 뒤 실제 사건 실패와 구분한다.

## 5. Evidence Pack PDF 장애

| 구분 | 확인 내용 |
| --- | --- |
| 경로 | Worker → Report S3, 사건 상태 `completed` |
| Alarm | Worker CPU·Memory, SQS Backlog·Oldest Message·DLQ |
| Logs | `/aws/ecs/bada-dev/worker`의 `pdf`, `report`, `evidence-pack`, `completed` |
| 주요 원인 | Worker handler 실패, 폰트·렌더링 오류, Report S3·KMS 권한 |
| 복구 | Worker 정상화·rollback 후 메시지 재처리, 애플리케이션 오류는 담당자에게 전달 |

```bash
aws s3 ls s3://bada-dev-report/packs/ --recursive | tail
aws s3api head-object --bucket bada-dev-report --key <pdf-key> \
  --query '{encryption:ServerSideEncryption,kmsKey:SSEKMSKeyId}'
```

## 6. 장애 처리 순서

```text
공통 상태 확인
→ Alarm과 Log Group으로 장애 단계 식별
→ 인프라·권한·연결 문제인지 기능 로직 문제인지 분리
→ 인프라 문제는 설정 수정 또는 rollback
→ 기능 문제는 로그·사건 ID·메시지 ID와 함께 담당자에게 전달
→ health·Alarm·Queue·결과 데이터 재검증
→ 조치 내용 기록
```
