# BADA 모니터링 운영 가이드

> 최종 갱신: 2026-07-03. 현재 배포된 관측성 스택 기준(초기 인계 문서에서 현행화).
> 관련: `docs/operations/sli-slo-definition.md`(SLI/SLO), `load-test/`(부하·오토스케일 검증), `docs/infra/implementation-status.md`(인프라 현황).

## 1. 관측성 스택 (현재)

| 계층 | 구성 | 상태 |
|------|------|------|
| 메트릭 수집 | Prometheus (ECS Fargate) — Backend `/metrics`, Worker `:9090/metrics` scrape | ✅ 두 타겟 UP |
| 시각화 | Grafana (ECS Fargate) — 대시보드 4개 | ✅ |
| 클라우드 지표 | CloudWatch — ECS/RDS/ALB/SQS + Container Insights, Alarm 14개 | ✅ |
| 분산 추적 | AWS X-Ray — Backend + Worker (사이드카) | ✅ |
| 알림 | Grafana Alerting → SNS → Email + CloudWatch Alarm → SNS | ✅ |

> Prometheus·Grafana는 관측 계층이라 `desired=1`(단일)로 둔다 — 서비스 트래픽 경로 밖이라 SPOF지만 사용자 영향 없음.

## 2. 접속 정보

```text
Grafana URL : https://monitor.badasoft.com
Username    : admin
Secret      : bada-dev/grafana-admin-password  (Secrets Manager)
```

```bash
aws secretsmanager get-secret-value \
  --secret-id bada-dev/grafana-admin-password \
  --query SecretString --output text
```

## 3. 대시보드 (4개)

Grafana `Dashboards → BADA` 폴더. 프로비저닝 소스: `monitoring/grafana/provisioning/dashboards/json/*.json`
(Grafana UI 수동 수정이 아니라 JSON 변경 후 Terraform apply로 영구 반영).

| 대시보드 | 데이터소스 | 내용 |
|----------|-----------|------|
| BADA Overview | Prometheus | 비즈니스 KPI(사건/분석/PDF), 요청량·에러율 |
| BADA Backend | Prometheus | HTTP 요청/지연/에러, 미들웨어 메트릭 |
| BADA Worker | Prometheus + CloudWatch | Worker 처리량·실패·지연, SQS 깊이 |
| BADA Infrastructure | CloudWatch | ECS CPU/Mem, RDS, ALB 4xx/5xx·요청량, SQS Visible·Oldest Age, **ECS Task Count(scale-out)** |

> **Infrastructure 대시보드 패널**은 `AWS/ECS`·`AWS/RDS`·`AWS/ApplicationELB`·`AWS/SQS`와
> `ECS/ContainerInsights`(Task Count) namespace를 사용한다. Container Insights가 켜져 있어야 한다(클러스터 설정 적용됨).
> Task Count 패널(RunningTaskCount/DesiredTaskCount)로 **오토스케일링 scale-out(1→2→3)** 을 시각적으로 확인한다.

## 4. Prometheus 타겟 & 메트릭

- 스크랩 대상: Prometheus 자기 자신, `bada-backend`(HTTPS `api.${domain}/metrics`), `bada-worker`(Cloud Map DNS `worker.${namespace}:9090`).
- Backend: `http_requests_total`, `http_request_duration_seconds_bucket` 등(미들웨어 계측).
- Worker(`prometheus_client`, `:9090`): 메시지 처리/실패, 처리 지연, Bedrock 호출, OCR/STT/PDF 건수, 분석 소요시간.

> 알림 규칙(§5)이 참조하는 정확한 지표명은 `monitoring/grafana/provisioning/alerting/rules.yml`과 worker 계측 코드가 단일 출처다.

## 5. Grafana Alerting

프로비저닝: `monitoring/grafana/provisioning/alerting/`(`contactpoints.yml`, `policies.yml`, `rules.yml`).

- **Contact Point**: `BADA-SNS` (Type=AWS SNS, Topic `bada-dev-alarm-notifications`) → 이메일
- **Notification Policy**: 기본 receiver `BADA-SNS`
- **Alert Rules: 10개 (G1~G10, 4개 그룹)**

| 그룹 | Rule | 조건 | 심각도 |
|------|------|------|--------|
| Service Health | G1 에러율 급증 | 5xx > 5% (5m) | critical |
| Service Health | G2 응답 지연 | p95 > 3s (5m) | warning |
| Service Health | G3 트래픽 제로 | 10분간 요청 0 (`noData=Alerting`) | critical |
| Worker | G4 Worker 실패율 | > 10% (5m) | warning |
| Worker | G5 Worker 처리 지연 | p95 > 60s (5m) | warning |
| Database | G6 RDS 커넥션 포화 | ≥ 80 (5m) | critical |
| Business | G7 분석 실패 연속 | 15분간 성공 0·실패 발생 | critical |
| Business | G8 OCR 실패율 | > 30% (5m) | warning |
| Business | G9 가용성 SLO 위반 | 가용성 < 99% (1h) | critical |
| Business | G10 분석 성공률 저하 | < 90% (30m) | critical |

> IAM: Grafana ECS Task Role(`bada-dev-monitoring-task-role`)은 `bada-dev-alarm-notifications` Topic에 `sns:Publish`만 허용(최소권한).

## 6. 알림 검증 절차

**Contact Point 테스트(가장 안전)**
1. Alerting → Contact points → `BADA-SNS` → ⋮ → Test
2. 수신 이메일에 `[BADA Alert] ...` 도착 확인

**G3 트래픽 제로 → 복구(자연 발생)**
1. 데모 환경은 트래픽이 없어 G3가 firing되는 게 정상
2. 요청 발생 후 10분 내 OK 전환 + "Resolved" 이메일 확인
   ```bash
   for i in $(seq 1 5); do curl -s https://api.badasoft.com/health; sleep 10; done
   ```

> 5xx 인위 발생(G1)은 백엔드 버그 주입이 필요해 비추천. Contact Point Test + G3 복구로 SNS 연동 검증은 충분.

## 7. 부하 테스트 & Auto Scaling 검증 (연계)

Auto Scaling(#4, Backend CPU 70% / Worker SQS backlog-per-task, min=1/max=3)의 실증은 `load-test/` 스크립트로 수행한다. 상세 설계·실행: `load-test/README.md`, `load-test/k6/README.md`.

| 시나리오 | 스크립트 | 관측 포인트(대시보드) |
|---------|---------|----------------------|
| Backend 스케일 메커니즘(CPU) | `k6/backend-autoscaling.js` (`MODE=cpu`, 기본) | Infra: Backend CPU% 70%↑ + **Task Count 1→2→3** |
| Backend 스케일아웃 **지연** | `k6/backend-autoscaling.js` (`MODE=latency`, 개방형) | Backend p95 지연 상승→**회복** + Task Count를 같은 타임라인에 겹쳐 캡처 |
| 현실적 읽기 부하 | `k6/backend-journey.js` | p95·처리량·에러율 (I/O 바운드라 CPU 낮게 유지 = 정상) |
| Worker 큐 적체 | `sqs/fill_backlog.py --watch` | Infra: SQS **Oldest Message Age** 상승→회복 + Worker **Task Count 1→3** + drain time |

> 검증의 핵심은 "scale-out이 발동했다"만이 아니라, **리액티브 오토스케일링의 지연(감지 3분 + Fargate 워밍업)** 구간에서
> 지연/큐 age가 어떻게 저하됐다가 증설 후 **회복**되는지다. 무중단 저지연을 원하면 min capacity 상향/예열이 필요하다는 한계까지 함께 서술한다.

## 8. 체크리스트

- [ ] Grafana 로그인 + 4개 대시보드 데이터 표시
- [ ] Prometheus 타겟(backend/worker) UP
- [ ] Contact Point `BADA-SNS` Test 이메일 수신
- [ ] Alert Rules 10개(G1~G10) BADA 폴더 존재
- [ ] Infra 대시보드 Task Count 패널로 scale-out 확인(부하 테스트 시)
- [ ] G3 Alerting → 요청 후 OK 전환 + Resolved 이메일
