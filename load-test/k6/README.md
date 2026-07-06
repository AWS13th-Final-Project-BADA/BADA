# BADA 부하 테스트 (k6) — Auto Scaling 실증 (#9)

Auto Scaling(#4)이 실제로 발동하는 것을 부하로 유발하고, Grafana/CloudWatch에서
scale-out/scale-in 그래프를 캡처하기 위한 스크립트다.

> ✅ 사전 조건: Auto Scaling이 apply되어 있어야 한다. 확인:
> ```bash
> aws application-autoscaling describe-scalable-targets \
>   --service-namespace ecs --region ap-northeast-2 --profile bada-team \
>   --query "ScalableTargets[].{id:ResourceId,min:MinCapacity,max:MaxCapacity}"
> ```
> `bada-dev-backend`, `bada-dev-worker` 또는 대상 환경의 Backend/Worker scalable target이 확인되면 준비 완료.

## ⚠️ 가드레일
- 대상 환경을 명시한다. 기본 대상은 `https://api.badasoft.com`이므로, `perf` 실행 시 `TARGET_URL`을 반드시 지정한다.
- 공유 검증 환경에서는 낮은 값으로 짧게 실행하고, 대규모 검증은 분리된 `perf` 환경에서 수행한다.
- 처음엔 `RATE` 또는 `VUS`를 낮게 잡아 짧게 시험한 뒤 단계적으로 올린다.
- Backend HTTP 부하와 Worker SQS backlog 부하는 목적이 다르므로 분리해서 실행한다.

## 1) Backend CPU 기반 스케일링 (주 시나리오)

`bada-dev-backend-cpu-tt` 정책(평균 CPU 70% Target Tracking)을 유발한다. **폐쇄형(ramping-vus)** 부하로
CPU를 70~100%에 꾸준히 유지해 스케일 알람(70% x 3분 연속)을 충족시킨다.

### 설치
- k6: https://k6.io/docs/get-started/installation/ (Windows: `winget install k6` 또는 `choco install k6`)

### 실행
```bash
# 기본 (VUS=40, sustain 8m, 총 약 14분)
k6 run load-test/k6/backend-autoscaling.js

# 부하 조절 (CPU가 75% 밑이면 VUS↑, 100% 붙어 타임아웃 많으면 VUS↓)
k6 run -e VUS=50 -e SUSTAIN=8m load-test/k6/backend-autoscaling.js

# perf 환경 대상
k6 run -e TARGET_URL="$PERF_API_URL" -e VUS=200 -e SUSTAIN=15m load-test/k6/backend-autoscaling.js

# MODE=latency: 개방형(constant-arrival-rate) + 실제 읽기 엔드포인트(/community/boards)로
#   scale-out 지연 구간의 p95 저하→회복을 측정 (메커니즘 증명이 아니라 "지연 특성")
k6 run -e MODE=latency -e RATE=100 -e SUSTAIN=8m load-test/k6/backend-autoscaling.js
#   RATE 튜닝: CPU 70%를 3분 못 넘기면 RATE↑, 타임아웃 폭주면 RATE↓
```

부하 단계: ramp-up 3m → **sustain 8m**(여기서 scale-out 1→2→3) → ramp-down 3m. 총 약 14분.

> ⚠️ 개방형(`ramping-arrival-rate`)은 작은 백엔드를 순식간에 포화시켜 타임아웃 폭주 →
> 완료 요청 급감 → CPU가 오히려 떨어져 스케일이 안 뜬다. 그래서 폐쇄형(`ramping-vus`)을 쓴다.

### 무엇을 캡처하나
1. **Grafana** `BADA Infrastructure` 대시보드
   - `Backend CPU %` 패널: 70% 돌파 구간
   - ECS RunningTaskCount(또는 서비스 desired) 증가: 1 → 2 → 3
2. **CloudWatch / CLI** — 스케일링 활동 텍스트 증거:
   ```bash
   aws application-autoscaling describe-scaling-activities \
     --service-namespace ecs --region ap-northeast-2 --profile bada-team \
     --resource-id service/bada-dev-cluster/bada-dev-backend \
     --query "ScalingActivities[].{time:StartTime,desc:Description,status:StatusCode}" --output table
   ```
3. 실행 중 실시간 태스크 수 확인:
   ```bash
   aws ecs describe-services --cluster bada-dev-cluster --services bada-dev-backend \
     --region ap-northeast-2 --profile bada-team \
     --query "services[0].{desired:desiredCount,running:runningCount}"
   ```

k6 종료 시 `load-test/k6/last-run-summary.json`에 요약이 저장된다(리포트 첨부용, git 미추적).

## 2) Worker SQS backlog 기반 스케일링 (선택)

`bada-dev-worker-backlog-tt` 정책은 **태스크당 대기 메시지 수**(`ApproximateNumberOfMessagesVisible / RunningTaskCount`, 목표 5)로 확장한다.
이건 HTTP 부하(k6)가 아니라 **SQS 큐에 메시지를 쌓아야** 유발된다.

- 권장: 실제 분석 요청(앱 업로드→분석)을 소량 반복해 큐를 채운다. 더미 메시지는 파싱 실패로 DLQ 노이즈를 만들고, 워커가 빨리 실패 처리하면 backlog가 유지되지 않아 스케일이 잘 안 뜬다.
- 대규모 backlog 검증은 `load-test/sqs/fill_backlog.py --queue <perf-queue>`로 대상 큐를 명시해 수행한다.
- 스케일 확인:
  ```bash
  aws application-autoscaling describe-scaling-activities \
    --service-namespace ecs --region ap-northeast-2 --profile bada-team \
    --resource-id service/bada-dev-cluster/bada-dev-worker --output table
  ```
- 주의: Worker는 `FARGATE_SPOT`이라 스케일아웃 태스크도 Spot으로 뜬다(비용 절감). SQS+DLQ 멱등성으로 중단에 안전.

## 종료 후
- 부하 종료 후 desired가 min(1)로 돌아오는지 확인(scale-in cooldown 300s).
- 캡처한 그래프/CLI 출력은 결과 기록에 첨부.
- 대규모 검증에서는 [`../perf-test-plan.md`](../perf-test-plan.md)의 종료 절차에 따라 큐, 임시 리소스, 알람 상태를 확인한다.
