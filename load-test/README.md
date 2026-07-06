# BADA 부하 테스트 (#9)

Auto Scaling(#4) 실증과 부하 특성 파악을 위한 부하 테스트 시나리오다. 각 시나리오는 증명하는 대상이 다르며, 실행 환경과 부하 규모에 따라 `dev` 검증과 `perf` 성능 검증으로 나누어 수행한다.

| 시나리오 | 파일 | 부하 성격 | 무엇을 증명 | 스케일 대상 | 외부 AI 호출 |
|---------|------|----------|------------|-----------|-------------|
| 1a. CPU 스트레스 | `k6/backend-autoscaling.js` (`MODE=cpu`, 기본) | 합성(폐쇄형, `/health`) | **오토스케일링 메커니즘이 실제 발동** | Backend CPU 70% | 없음 |
| 1b. 스케일아웃 지연 | `k6/backend-autoscaling.js` (`MODE=latency`) | 개방형(constant-arrival-rate), 실제 읽기 엔드포인트 | **scale-out 지연 구간 p95 저하→회복** | Backend CPU 70% | 없음 |
| 2. 사용자 여정 | `k6/backend-journey.js` | 현실적 읽기(인증+DB+선택적 번역) | **동시 사용자 하 지연/처리량/에러율**, 실부하는 I/O 바운드임을 확인 | 대개 미발동(I/O 바운드) | 선택적 |
| 3. Worker 적체 | `sqs/fill_backlog.py --watch` | 현실적 서지(SQS 큐 적체) | **비동기 Worker scale-out + 큐 age/드레인 회복** | Worker SQS backlog | 없음(bogus case_id) |

> 해석 기준: 1번은 스케일링 정책이 실제로 동작하는지 검증하고, 2·3번은 BADA의 주요 트래픽 유형인 읽기 I/O와 분석 서지를 재현한다. 실제 사용자 여정에서 Backend CPU가 낮게 유지되는 경우는 비정상이라기보다 I/O 바운드 특성으로 해석한다.

## 실행 환경 구분

| 환경 | 목적 | 권장 부하 | 주의사항 |
| --- | --- | --- | --- |
| `dev` | 기능 통합 후 Auto Scaling 동작 확인 | 낮음~중간 | 운영 중인 검증 리소스와 큐를 사용하므로 짧게 실행하고 즉시 정리한다. |
| `perf` | 격리된 성능 검증과 대규모 부하 관측 | 중간~높음 | 별도 state/tfvars/리소스 prefix를 사용하고, 실행 후 제거한다. |

대규모 테스트는 `perf` 환경에서 수행한다. `perf` 환경은 기존 `dev`/`prod` 리소스와 DB, SQS, S3, ECS Cluster, CloudWatch Log Group을 분리해야 한다. 자세한 절차는 [`perf-test-plan.md`](./perf-test-plan.md)를 따른다.

## 공통 가드레일
- 대상 환경과 URL을 실행 전에 명시한다. 기본값은 `dev`이므로, `perf` 실행 시 반드시 `TARGET_URL`, 큐 이름 또는 큐 URL을 명시한다.
- 운영·검증 트래픽과 겹치지 않는 실행 창을 확보하고, 시작/종료 시각을 팀에 공유한다.
- 낮은 값으로 사전 점검 후 단계적으로 부하를 올린다.
- AWS 자격증명은 **`bada-team` 프로파일**(BADA 계정 165749212250). `default`는 다른 계정이라 주의.
- Auto Scaling 적용 확인:
  ```bash
  aws application-autoscaling describe-scalable-targets \
    --service-namespace ecs \
    --region ap-northeast-2 \
    --profile bada-team
  ```
- 외부 AI 서비스 호출이 포함된 시나리오는 별도 승인 후 소량으로만 수행한다. 대규모 부하에서는 `mock`/`local` 모드를 우선한다.
- 종료 후 큐, ECS desired count, CloudWatch Alarm, 테스트 데이터, 임시 리소스를 확인한다.

## 1. Backend 스케일 (메커니즘 + 지연)
```bash
# 1a. 메커니즘 증명 (폐쇄형 /health, CPU 태우기)
k6 run load-test/k6/backend-autoscaling.js
# 1b. 스케일아웃 지연 측정 (개방형, 실제 읽기 엔드포인트 /community/boards)
k6 run -e MODE=latency -e RATE=100 load-test/k6/backend-autoscaling.js
```
확인: Grafana `BADA Infrastructure`의 Backend CPU% 70%↑ + **Backend Task Count(1→2→3)** 패널. 1b는 p95 지연 상승→회복 곡선을 Task Count와 같은 타임라인에 겹쳐 캡처(리액티브 스케일링은 감지 3분 + Fargate 워밍업 동안 지연이 오르는 게 정상 — 회복을 보는 게 목적). 텍스트 증거: `describe-scaling-activities`(backend).

## 2. 사용자 여정 (현실적 읽기 부하)
```bash
k6 run load-test/k6/backend-journey.js               # 토큰 없이 공개 엔드포인트
k6 run -e TOKEN=<jwt> load-test/k6/backend-journey.js            # 인증 여정
k6 run -e TOKEN=<jwt> -e CASE_ID=<case> load-test/k6/backend-journey.js  # + 분석 조회(실시간 번역)
```
- `TOKEN`: 로그인된 앱의 access_token, 또는 `jwt_secret`(Secrets Manager `bada-dev/app-secrets`)으로 서명해 발급.
- 확인: p95 지연/처리량/에러율. CPU는 낮게 유지될 수 있음(I/O 바운드 — 정상).

## 3. Worker SQS 적체 (비동기 서지, Worker 스케일 + 큐 지연)
```bash
# PowerShell: $env:AWS_PROFILE="bada-team"
python load-test/sqs/fill_backlog.py --count 6000 --watch   # 적체 투입 + 드레인 곡선 관측
```
- 원리: 없는 case_id → 워커가 첫 DB 조회에서 실패(Bedrock 미호출). 테스트 창엔 DLQ로 안 감(visibility 900s).
- 확인: Grafana `BADA Infrastructure`의 **SQS Oldest Message Age** 상승→회복 + **Worker Task Count 1→3**. `--watch`가 elapsed/visible/in-flight/oldest_age를 주기 출력해 드레인 곡선·소요시간을 캡처(비동기의 "지연" = 큐 대기시간). `describe-scaling-activities`(worker)로 텍스트 증거.
- ⚠️ bogus 메시지라 처리시간은 비현실적으로 짧음 → 여기서 보는 건 "적체→소진(드레인) 회복"이지 실제 분석 처리 latency가 아니다. 실제 end-to-end 지연은 유효 case를 소량 실행해야 측정 가능(Bedrock 비용 발생).
- **정리(필수)**: 종료 후 `python load-test/sqs/fill_backlog.py --purge` 로 잔여 메시지 제거(재출현/DLQ 방지). purge는 큐 전체를 비우므로 실제 트래픽 없는 창에서만.
- 부작용: 워커 실패 메트릭이 합성적으로 튄다(정상). backlog가 안 쌓이면 `--count`를 늘린다(워커 소비속도보다 많아야 유지됨).

## 산출물

부하 테스트 후 아래 자료를 남긴다.

- k6 summary JSON(`load-test/k6/last-*.json`, git 미추적)
- Grafana/CloudWatch 캡처
  - Backend CPU/Memory
  - ECS RunningTaskCount / DesiredCount
  - ALB 5xx / target health
  - RDS CPU / connections
  - SQS visible / in-flight / oldest message age
  - Worker task count / Worker Prometheus metrics
- `describe-scaling-activities` 출력
- 테스트 조건표
  - 대상 환경
  - 테스트 시간
  - VU/RPS/message count
  - p95 latency
  - error rate
  - scale-out/scale-in 시각
- 정리 결과
  - 큐 잔여 메시지
  - ECS desired count 복귀 여부
  - 임시 리소스 제거 여부
