# BADA 모니터링 운영 가이드

> 최종 갱신: 2026-07-03. 현재 배포된 관측성 스택 기준(초기 인계 문서에서 현행화).
> 관련: `docs/operations/sli-slo-definition.md`(SLI/SLO), `load-test/`(부하·오토스케일 검증), `docs/infra/implementation-status.md`(인프라 현황).

## 1. 관측성 스택 (현재)

| 계층 | 구성 | 상태 |
|------|------|------|
| 메트릭 수집 | Prometheus (ECS Fargate) — Backend `/metrics`, Worker `:9090/metrics` scrape | ✅ 두 타겟 UP |
| 시각화 | Grafana (ECS Fargate) — 대시보드 7개 (Overview 공용 + dev 3 + prod 3) | ✅ |
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

## 3. 대시보드 (7개)

Grafana `Dashboards → BADA` 폴더. 프로비저닝 소스: `monitoring/grafana/provisioning/dashboards/json/*.json`
(Grafana UI 수동 수정이 아니라 JSON 변경 후 Terraform apply로 영구 반영).

| 대시보드 | 데이터소스 | 내용 |
|----------|-----------|------|
| BADA Overview | Prometheus | **dev+prod 공용** — 상단 `env` 셀렉터로 환경 선택/합산(`by (env)`). HTTP 요청량·에러율·P95·분석 실행. (Worker 처리량은 dev만 — §9) |
| BADA Dev Backend | Prometheus | (**dev**) HTTP 요청/상태코드/에러율/지연(P50·95·99)/상위 경로, 분석·OCR (`env="dev"` 필터) |
| BADA Dev Worker | Prometheus + CloudWatch | (**dev**) Worker 처리량·결과·처리시간·실패율(Prometheus), SQS 대기·In-Flight(CloudWatch) |
| BADA Dev Infrastructure | CloudWatch | (**dev**) ECS CPU/Mem, RDS, ALB 4xx/5xx·요청량, SQS Visible·Oldest Age, **ECS Task Count(scale-out)** |
| BADA Prod Backend | Prometheus | (**prod, 크로스 환경**) prod backend HTTP 요청/상태코드/에러율/지연/상위 경로 (`env="prod"`). §9 참조 |
| BADA Prod Worker | CloudWatch | (**prod, 크로스 환경**) Worker ECS CPU/Mem, SQS 대기·In-Flight·Oldest Age, Task Count. prod worker는 Prometheus 미수집 → CloudWatch. §9 참조 |
| BADA Prod Infrastructure | CloudWatch | (**prod, 크로스 환경**) prod 클러스터의 ECS/RDS/ALB/SQS + Task Count. §9 참조 |

> **Infrastructure 대시보드 패널**은 `AWS/ECS`·`AWS/RDS`·`AWS/ApplicationELB`·`AWS/SQS`와
> `ECS/ContainerInsights`(Task Count) namespace를 사용한다. Container Insights가 켜져 있어야 한다(클러스터 설정 적용됨).
> Task Count 패널(RunningTaskCount/DesiredTaskCount)로 **오토스케일링 scale-out(1→2→3)** 을 시각적으로 확인한다.

## 4. Prometheus 타겟 & 메트릭

- 스크랩 대상: Prometheus 자기 자신, `bada-backend`(HTTPS `api.${domain}/metrics`, 라벨 `env="dev"`), `bada-worker`(Cloud Map DNS `worker.${namespace}:9090`, 라벨 `env="dev"`).
- **크로스 환경(prod)**: `prod_monitoring_enabled=true` 시 `bada-backend-prod` 타겟(HTTPS `api.${prod_domain}/metrics`, 라벨 `env="prod"`)이 추가된다. prod backend는 공인 ALB로 노출돼 인터넷(NAT egress) 경유로 스크랩된다. §9 참조.
- Backend: `http_requests_total`, `http_request_duration_seconds_bucket` 등(미들웨어 계측).
- Worker(`prometheus_client`, `:9090`): 메시지 처리/실패, 처리 지연, Bedrock 호출, OCR/STT/PDF 건수, 분석 소요시간.

> 알림 규칙(§5)이 참조하는 정확한 지표명은 `monitoring/grafana/provisioning/alerting/rules.yml`과 worker 계측 코드가 단일 출처다.
> ⚠️ prod 타겟을 켜면 `env` 라벨 없는 기존 알림 쿼리(예: G1·G3·G9)는 dev+prod를 **합산**한다. 환경별로 분리하려면 쿼리에 `{env="dev"}`(또는 `{env="prod"}`)를 추가한다.

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

- [ ] Grafana 로그인 + 7개 대시보드 데이터 표시 (Overview 공용 + dev 3 + prod 3)
- [ ] Prometheus 타겟(dev backend/worker) UP (prod 활성 시 `bada-backend-prod` 포함)
- [ ] Contact Point `BADA-SNS` Test 이메일 수신
- [ ] Alert Rules 10개(G1~G10) BADA 폴더 존재
- [ ] Infra 대시보드 Task Count 패널로 scale-out 확인(부하 테스트 시)
- [ ] G3 Alerting → 요청 후 OK 전환 + Resolved 이메일

## 9. 크로스 환경(prod) 관측 — dev 스택에서 prod 보기

dev/prod/perf는 **각각 별도 Terraform state/VPC**이며, 각 환경이 자기 Prometheus+Grafana를 띄운다. 그래서 `monitor.badasoft.com`(dev) Grafana는 기본적으로 dev 리소스만 본다. prod 현황을 같은 화면에서 보기 위해 아래를 추가했다.

### 대시보드 구성 (dev/prod 대칭)

환경 구분을 명확히 하기 위해 dev 대시보드는 이름에 **Dev**를 붙였고, prod는 dev와 유사한 세트를 갖춘다. **Overview는 dev+prod 공용**이다.

| 구분 | 대시보드 | 데이터소스 |
|------|----------|-----------|
| 공용 | BADA Overview | Prometheus (`env` 셀렉터로 dev/prod 선택·합산) |
| dev | BADA Dev Backend / Dev Worker / Dev Infrastructure | Prometheus(+CloudWatch) |
| prod | BADA Prod Backend / Prod Worker / Prod Infrastructure | Prod Backend=Prometheus(`env="prod"`), Prod Worker/Infra=CloudWatch |

### 어떻게 동작하나

| 대상 | 방식 | 근거 |
|------|------|------|
| prod **backend** 앱 메트릭 | Prometheus가 공인 ALB(`api.prod.badasoft.com/metrics`)를 인터넷 경유로 스크랩 (`env="prod"` 라벨) → **BADA Prod Backend** | backend `/metrics`가 ALB로 노출됨 |
| prod **ECS/RDS/ALB/SQS/Task Count** | Grafana CloudWatch datasource가 prod 리소스 이름으로 조회 (같은 계정·리전) → **BADA Prod Worker / Prod Infrastructure** | 모니터링 Task Role이 `cloudwatch:*` 읽기 보유 |
| prod **worker** 앱 메트릭(처리량·처리시간 등) | ❌ 미수집 (다른 VPC의 Cloud Map이라 크로스-VPC 스크랩 불가) → **CloudWatch(Container Insights)** 로 대체 관측 | Prometheus DNS SD는 VPC 내부 전용 |

> 원칙: prod worker의 상세 애플리케이션 메트릭까지 Prometheus로 모으려면 VPC 피어링 또는 중앙 관측 계정(remote_write)이 필요하다. 데모/기간 대비 과하여 **CloudWatch 기반 관측으로 갈음**한다(ECS CPU/메모리·Task Count·SQS는 CloudWatch로 충분히 확인 가능).
> Overview의 **Worker 메시지 처리량** 패널은 같은 이유로 prod가 표시되지 않고 dev만 나온다.

### 활성화 절차 (Terraform)

```hcl
# infra/env/dev.tfvars (또는 실행 시 -var)
prod_monitoring_enabled = true          # prod backend 스크랩 + prod ALB arn_suffix 조회 on
prod_domain_name        = "prod.badasoft.com"
# 리소스 이름은 bada-prod-* 규칙 기본값 사용. 다르면 아래로 override.
# prod_ecs_cluster_name     = "bada-prod-cluster"
# prod_backend_service_name = "bada-prod-backend"
# prod_worker_service_name  = "bada-prod-worker"
# prod_rds_instance_id      = "bada-prod-postgres-multiaz"
# prod_sqs_queue_name       = "bada-prod-analysis"
# prod_sqs_dlq_name         = "bada-prod-analysis-dlq"
# prod_alb_name             = "bada-prod-alb"
```

```bash
# dev state에서 적용 (모니터링 스택은 dev에 있음)
terraform init -reconfigure -backend-config=backends/dev.hcl
terraform plan  -var-file=env/dev.tfvars
terraform apply -var-file=env/dev.tfvars   # 담당자만
```

- 적용 후 Grafana에 **BADA Prod Backend / Prod Worker / Prod Infrastructure** 대시보드가 나타나고, **BADA Overview**의 `env` 셀렉터에서 `prod`를 선택할 수 있다.
- `prod_monitoring_enabled=false`(기본)이면 prod backend 스크랩 타깃과 prod ALB arn_suffix 조회를 하지 않아 dev plan/apply가 prod 존재 여부와 무관하게 안전하다. 이 경우 prod 대시보드는 provisioning되지만 데이터가 비어 보인다(ALB 패널은 arn_suffix 없이 무데이터, backend는 스크랩 타깃 미생성). 이름 기반(ECS/RDS/SQS) 패널은 prod가 떠 있으면 데이터를 보여준다.
- **주의**: `prod_monitoring_enabled=true`는 prod 스택(특히 `bada-prod-alb`)이 실제 배포돼 있어야 한다(`data "aws_lb" "prod"` 조회). 미배포 상태에서 켜면 apply가 실패한다.

### 종료(7/10) 정리
- `prod_monitoring_enabled=false`로 되돌리면 prod backend 스크랩 타깃과 ALB 조회가 제거된다. prod 대시보드(`bada-prod-*.json`) 자체는 남지만(무해), 원하면 해당 프로비저닝 라인을 제거한다.
