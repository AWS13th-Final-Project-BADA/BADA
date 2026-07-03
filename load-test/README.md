# BADA 부하 테스트 (#9)

Auto Scaling(#4) 실증과 부하 특성 파악을 위한 3종 시나리오. 각각 증명하는 것이 다르다.

| 시나리오 | 파일 | 부하 성격 | 무엇을 증명 | 스케일 대상 | 비용 |
|---------|------|----------|------------|-----------|------|
| 1a. CPU 스트레스 | `k6/backend-autoscaling.js` (`MODE=cpu`, 기본) | 합성(폐쇄형, `/health`) | **오토스케일링 메커니즘이 실제 발동** | Backend CPU 70% | 0 |
| 1b. 스케일아웃 지연 | `k6/backend-autoscaling.js` (`MODE=latency`) | 개방형(constant-arrival-rate), 실제 읽기 엔드포인트 | **scale-out 지연 구간 p95 저하→회복** | Backend CPU 70% | 0 |
| 2. 사용자 여정 | `k6/backend-journey.js` | 현실적 읽기(인증+DB+번역) | **동시 사용자 하 지연/처리량/에러율**, 실부하는 I/O 바운드임을 확인 | (대개 미발동 — I/O 바운드) | 0 |
| 3. Worker 적체 | `sqs/fill_backlog.py --watch` | 현실적 서지(SQS 큐 적체) | **비동기 Worker scale-out + 큐 age/드레인 회복** | Worker SQS backlog | 0 (bogus case_id) |

> 포트폴리오 서술: 1번으로 "정책이 동작함"을 증명하고, 2·3번으로 "실제 BADA 트래픽 유형(읽기 I/O + 분석 서지)"을 재현한다. 실사용 백엔드는 CPU보다 I/O 바운드라 CPU 스케일이 잘 안 뜨는 것도 정직한 발견이다.

## 공통 가드레일
- 대상은 운영 데모 엔드포인트/큐. **팀 공지 + 데모·리허설 시간 회피.** 낮은 값으로 시험 후 본 실행.
- AWS 자격증명은 **`bada-team` 프로파일**(BADA 계정 165749212250). `default`는 다른 계정이라 주의.
- apply 확인: `aws application-autoscaling describe-scalable-targets --service-namespace ecs --region ap-northeast-2 --profile bada-team`

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
