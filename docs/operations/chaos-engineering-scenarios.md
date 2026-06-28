# 카오스 엔지니어링 테스트 시나리오

> 시점: Phase 4 (Auto Scaling + k6 부하 테스트 이후)
> 목적: 복구 메커니즘이 실제로 동작하는지 실증
> 전제: ECS circuit breaker, SQS DLQ, ALB health check, Auto Scaling 적용 완료

---

## 테스트 환경

```
클러스터: bada-dev-cluster
리전: ap-northeast-2
모니터링: monitor.badasoft.com (Grafana)
```

---

## 시나리오 1: Backend 태스크 강제 종료

**검증 대상**: ECS circuit breaker + ALB health check 자동 복구

**절차:**

```bash
# 1. 현재 태스크 확인
aws ecs list-tasks --cluster bada-dev-cluster --service-name bada-dev-backend --query "taskArns[0]" --output text

# 2. 태스크 강제 종료
aws ecs stop-task --cluster bada-dev-cluster --task <task-arn> --reason "chaos-test-backend-kill"

# 3. 타이머 시작 — 복구 시간 측정
```

**기대 결과:**

| 시간 | 상태 |
|------|------|
| 0초 | 태스크 STOPPED |
| ~10초 | ALB target unhealthy → 503 반환 |
| ~30초 | ECS가 새 태스크 PENDING |
| ~60초 | 새 태스크 RUNNING + ALB target healthy |
| ~90초 | `api.badasoft.com/health` → 200 정상 |

**검증 명령어:**

```bash
# 서비스 상태 확인 (runningCount가 1로 돌아와야 함)
aws ecs describe-services --cluster bada-dev-cluster --services bada-dev-backend \
  --query "services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}"

# ALB target health 확인
aws elbv2 describe-target-health --target-group-arn <backend-tg-arn>

# 최종 health check
curl -s https://api.badasoft.com/health
```

**성공 기준:**
- [ ] 새 태스크 90초 이내 healthy
- [ ] 사용자 요청 502/503 지속 시간 < 60초
- [ ] Grafana에서 에러율 spike → 복구 그래프 확인

---

## 시나리오 2: Worker 태스크 강제 종료 (메시지 처리 중)

**검증 대상**: SQS visibility timeout + DLQ + 멱등성 재처리

**절차:**

```bash
# 1. 테스트 메시지 발행 (분석 요청)
aws sqs send-message --queue-url <sqs-url> \
  --message-body '{"case_id":"chaos-test-001","action":"analyze_case"}'

# 2. Worker가 수신한 직후 태스크 강제 종료
aws ecs stop-task --cluster bada-dev-cluster --task <worker-task-arn> --reason "chaos-test-worker-kill"

# 3. 대기 (visibility timeout 15분 후 메시지 재노출)
```

**기대 결과:**

| 시간 | 상태 |
|------|------|
| 0초 | Worker 태스크 STOPPED, 메시지 in-flight |
| ~30초 | ECS가 새 Worker 태스크 기동 |
| ~60초 | 새 Worker RUNNING, SQS 폴링 시작 |
| 15분 | visibility timeout 만료 → 메시지 다시 보임 |
| 15분+α | 새 Worker가 메시지 재처리 |

**검증:**

```bash
# SQS 메시지 수 확인 (처리 완료 후 0이어야 함)
aws sqs get-queue-attributes --queue-url <sqs-url> \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

# DLQ 확인 (정상 재처리 시 DLQ에 안 빠져야 함)
aws sqs get-queue-attributes --queue-url <dlq-url> \
  --attribute-names ApproximateNumberOfMessages
```

**성공 기준:**
- [ ] 새 Worker 60초 이내 기동
- [ ] 메시지 유실 없음 (visibility timeout 후 재처리)
- [ ] DLQ에 메시지 0개 (정상 재처리 완료)
- [ ] 결과 중복 없음 (멱등성)

---

## 시나리오 3: 부하 중 태스크 킬 (k6 + 카오스)

**검증 대상**: Auto Scaling + 장애 복합 상황 대응

**절차:**

```bash
# 1. k6 부하 시작 (별도 터미널)
k6 run --vus 50 --duration 5m load-test.js

# 2. 부하 진행 중 1분 후 Backend 태스크 1개 kill
aws ecs stop-task --cluster bada-dev-cluster --task <task-arn> --reason "chaos-under-load"

# 3. Grafana에서 실시간 관찰
```

**기대 결과:**

| 시간 | 상태 |
|------|------|
| 0~1분 | k6 부하 → Auto Scaling이 태스크 2~3개로 증가 |
| 1분 | 태스크 1개 kill |
| 1분~2분 | 남은 태스크가 트래픽 흡수 + ECS가 새 태스크 기동 |
| 2분~ | 태스크 수 복원, 에러율 정상 |
| 5분 | k6 종료, 스케일인 |

**Grafana 캡처 포인트:**
1. Auto Scaling 발동 시점 (태스크 수 증가)
2. 태스크 kill → 에러율 spike
3. 복구 → 에러율 정상 복귀
4. 스케일인 (부하 해소 후)

**성공 기준:**
- [ ] kill 후 에러율 < 5% (남은 태스크가 흡수)
- [ ] 60초 이내 태스크 수 복원
- [ ] 전체 테스트 중 성공률 > 95%

---

## 시나리오 4: SQS 메시지 폭증 (Worker Auto Scaling)

**검증 대상**: SQS backlog 기반 Worker Auto Scaling

**절차:**

```bash
# 1. 더미 메시지 20개 한번에 발행
for i in $(seq 1 20); do
  aws sqs send-message --queue-url <sqs-url> \
    --message-body "{\"case_id\":\"chaos-batch-$i\",\"action\":\"analyze_case\"}"
done

# 2. CloudWatch 메트릭 + ECS 태스크 수 관찰
```

**기대 결과:**
- SQS `ApproximateNumberOfMessagesVisible` > 임계치 → Worker 스케일아웃
- 메시지 처리 완료 후 스케일인

**성공 기준:**
- [ ] Worker 태스크 1 → 2~3개 자동 증가
- [ ] 모든 메시지 처리 완료 (큐 0)
- [ ] DLQ 0개 (더미 메시지라 실패 가능 → 이 경우 DLQ 수 = 기대치로 조정)

---

## 시나리오 5: RDS failover (Multi-AZ 적용 후)

**검증 대상**: RDS 자동 failover + 어플리케이션 재연결

**절차:**

```bash
# RDS failover 트리거 (Multi-AZ 시에만 가능)
aws rds reboot-db-instance --db-instance-identifier bada-dev-db --force-failover
```

**기대 결과:**

| 시간 | 상태 |
|------|------|
| 0초 | failover 시작 |
| 30~60초 | 새 Primary 승격 |
| 60~90초 | Backend/Worker DB 재연결 |

**성공 기준:**
- [ ] failover 완료 90초 이내
- [ ] Backend API 정상 응답 복귀
- [ ] 데이터 유실 없음

---

## 실행 체크리스트

**사전 준비:**
- [ ] Grafana 대시보드 열어두기 (실시간 관찰)
- [ ] CloudWatch Alarm 확인 (alert 발생 예상)
- [ ] 팀원에게 카오스 테스트 시간 공유 (혼란 방지)
- [ ] 테스트 후 리소스 정리 (더미 메시지 등)

**실행 순서:**
1. 시나리오 1 (Backend kill) — 가장 단순, 워밍업
2. 시나리오 2 (Worker kill) — 메시지 재처리 확인
3. 시나리오 4 (SQS 폭증) — Auto Scaling 확인
4. 시나리오 3 (부하 + kill) — 복합 상황
5. 시나리오 5 (RDS failover) — Multi-AZ 적용 후에만

**산출물:**
- Grafana 스크린샷 (각 시나리오별 spike → 복구 그래프)
- 복구 시간 측정 테이블
- 성공/실패 체크리스트 완성본
- 발표 자료 1~2 슬라이드

---

## 참고

- ECS circuit breaker: `deployment_circuit_breaker { enable = true, rollback = true }`
- SQS DLQ: `maxReceiveCount = 5`, visibility timeout 15분
- Auto Scaling: Backend CPU 70%, Worker SQS backlog 기반
- 런북: `docs/runbooks/demo-incident-response.md`
