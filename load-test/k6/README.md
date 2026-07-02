# BADA 부하 테스트 (k6) — Auto Scaling 실증 (#9)

Auto Scaling(#4)이 실제로 발동하는 것을 부하로 유발하고, Grafana/CloudWatch에서
scale-out/scale-in 그래프를 캡처하기 위한 스크립트다.

> ✅ 사전 조건: Auto Scaling이 apply되어 있어야 한다. 확인:
> ```bash
> aws application-autoscaling describe-scalable-targets \
>   --service-namespace ecs --region ap-northeast-2 --profile bada-team \
>   --query "ScalableTargets[].{id:ResourceId,min:MinCapacity,max:MaxCapacity}"
> ```
> `bada-dev-backend`, `bada-dev-worker`가 min=1/max=3으로 나오면 준비 완료.

## ⚠️ 가드레일 (공용 데모 환경)
- 대상은 운영 데모 엔드포인트(`api.badasoft.com`)다. **팀에 실행 시간대를 공지**하고 데모/리허설과 겹치지 않게 한다.
- 처음엔 `PEAK_RATE`를 낮게(예: 60) 잡아 짧게 시험한 뒤 본 실행한다.
- Backend만 대상으로 한다(사용자 대면). Worker 스케일링은 아래 별도 섹션 참고.

## 1) Backend CPU 기반 스케일링 (주 시나리오)

`bada-dev-backend-cpu-tt` 정책(평균 CPU 70% Target Tracking)을 유발한다.
Backend Task가 0.25 vCPU라 수백 RPS면 CPU가 빠르게 70%를 넘어 1→2→3으로 확장된다.

### 설치
- k6: https://k6.io/docs/get-started/installation/ (Windows: `winget install k6` 또는 `choco install k6`)

### 실행
```bash
# 기본 (peak 200 RPS, 총 약 16분)
k6 run load-test/k6/backend-autoscaling.js

# 낮게 시험 실행
k6 run -e PEAK_RATE=60 load-test/k6/backend-autoscaling.js

# 대상/엔드포인트 변경
k6 run -e TARGET_URL=https://api.badasoft.com -e ENDPOINT=/health -e PEAK_RATE=200 \
  load-test/k6/backend-autoscaling.js
```

부하 단계(스크립트 내 stages): warm-up 2m → ramp-up 3m → **sustain 7m**(여기서 scale-out) → ramp-down 4m(scale-in 관찰). 총 약 16분.

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
- 스케일 확인:
  ```bash
  aws application-autoscaling describe-scaling-activities \
    --service-namespace ecs --region ap-northeast-2 --profile bada-team \
    --resource-id service/bada-dev-cluster/bada-dev-worker --output table
  ```
- 주의: Worker는 `FARGATE_SPOT`이라 스케일아웃 태스크도 Spot으로 뜬다(비용 절감). SQS+DLQ 멱등성으로 중단에 안전.

## 종료 후
- 부하 종료 후 desired가 min(1)로 돌아오는지 확인(scale-in cooldown 300s).
- 캡처한 그래프/CLI 출력은 발표 자료에 첨부.
