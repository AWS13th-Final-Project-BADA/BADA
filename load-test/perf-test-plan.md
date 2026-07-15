# BADA perf 환경 성능 검증 계획

이 문서는 BADA의 대규모 부하 특성을 검증하기 위한 `perf` 환경 실행 기준을 정의한다. `perf` 환경은 기존 `dev`/`prod` 리소스와 분리된 성능 검증 전용 환경이며, 테스트 종료 후 제거하는 것을 기본 원칙으로 한다.

더 큰 규모의 운영 실험은 [`perf-scale-experiment.md`](./perf-scale-experiment.md)를 따른다. 해당 문서는 1,000/3,000/5,000~10,000 VU 단계 테스트, RDS/Backend/Worker 사이징 비교, SQS 10만 건 drain, 장애 주입 테스트와 결과 정리 구조를 별도로 정의한다.

## 1. 목적

- Backend API의 처리량, 지연, 오류율을 단계별 부하에서 관측한다.
- ECS Auto Scaling이 부하 증가에 따라 정상적으로 scale-out 되는지 확인한다.
- SQS 기반 비동기 분석 파이프라인에서 backlog 증가와 Worker scale-out, drain 회복을 관측한다.
- RDS, ALB, ECS, SQS, CloudWatch, Grafana 지표를 함께 수집해 병목 지점을 식별한다.
- 성능 검증 과정과 결과를 재현 가능한 절차로 남긴다.

## 2. 환경 원칙

`perf` 환경은 다음 리소스를 `dev`/`prod`와 분리한다.

| 구분 | 분리 기준 |
| --- | --- |
| Terraform state | `bada/perf/terraform.tfstate` |
| 리소스 prefix | `bada-perf-*` |
| ECS Cluster/Service | Backend, Worker, Grafana/Prometheus 필요 시 별도 생성 |
| RDS | 별도 DB 인스턴스 또는 별도 복원 DB |
| SQS/DLQ | 별도 분석 큐와 DLQ |
| S3 | 별도 evidence/report bucket |
| CloudWatch | 별도 Log Group/Alarm prefix |
| 도메인 | **현재 ALB DNS HTTP 사용**(도메인/HTTPS 미사용). `api.perf.badasoft.com`은 `badasoft.com` 위임 복구 시에만 쓸 수 있는 옵션 |

운영과 동일한 3-tier 네트워크 구조가 반드시 필요한 테스트가 아니라면, `perf`는 단순화된 네트워크 구성을 사용할 수 있다. 예를 들어 NAT Gateway를 추가하지 않고 ECS를 public subnet에 배치해 계정 단위 NAT/EIP 사용량을 줄일 수 있다.

권장 기본값:

```hcl
environment            = "perf"
ecs_in_private_subnets = false
nat_gateway_enabled    = false
frontend_enabled       = false

backend_provider_mode  = "local"
worker_provider_mode   = "local"
backend_transcribe_mode = "local"
worker_transcribe_mode  = "local"

backend_autoscaling_enabled = true
worker_autoscaling_enabled  = true
backend_min_capacity = 2
backend_max_capacity = 20
worker_min_capacity  = 2
worker_max_capacity  = 30
```

외부 AI 서비스 호출은 대규모 부하에서 제외하고, 필요 시 별도 소량 E2E 검증으로 분리한다.

### 2.1 리허설로 검증된 구조 (2026-07-06)

2026-07-06 기립 리허설에서 아래 구조가 생성·삭제됨을 기록했다.

> ⚠️ **정정(2026-07-07)**: 아래 표의 "Route53 + ACM + WAF + ALB HTTPS(443)" 및 `https://api.perf.badasoft.com/health 200`은 7/6 리허설 시점 기록이다. 이후 검증에서 **`badasoft.com` 공인 DNS 위임이 끊겨 있어** ACM DNS 검증이 완료될 수 없음이 확인됐다(§4.1.1 및 개인 execution-log 참조). **실제 본 실험(perf-small/medium)은 도메인/HTTPS를 사용하지 않고 ALB DNS HTTP로 수행**했다. HTTPS 경로는 도메인 위임 복구 시에만 유효하다.

| 항목 | 리허설 목표 (2026-07-06) | 본 실험 실제 (2026-07-07) |
| --- | --- | --- |
| Terraform state | `bada/perf/terraform.tfstate` | 동일 |
| 리소스 prefix | `bada-perf-*` | 동일 |
| 도메인 | `perf.badasoft.com`, `api.perf.badasoft.com` | **미사용** (DNS 위임 끊김) |
| 진입/보안 | Route53 + ACM + WAF + ALB HTTPS(443) | **WAF + ALB HTTP(80)**, ACM/Route53 미생성 |
| 접속 URL | `https://api.perf.badasoft.com` | **`http://<perf-alb-dns>`** |
| ECS 배치 | public subnet + public IP | 동일 |
| NAT Gateway | 없음 (EIP 미사용) | 동일 |
| 분리 리소스 | RDS / SQS·DLQ / S3 / Secrets / CloudWatch 모두 `bada-perf-*` 별도 | 동일 |

> "리허설 목표"는 7/6 기립 리허설이 의도한 도메인+HTTPS 구성이고, "본 실험 실제"는 DNS 위임 문제로
> 도메인/HTTPS를 제외하고 ALB DNS HTTP로 수행한 perf-small/medium 실험의 실제 구성이다.

> Route53 레코드(`perf.badasoft.com`, `api.perf.badasoft.com`)는 기존 dev(`badasoft.com`,
> `api.badasoft.com`)/prod(`prod.badasoft.com`, `api.prod.badasoft.com`)와 이름이 겹치지 않는
> **additive record**다. 부모 존에 추가만 되고 기존 레코드를 변경하지 않는다(리허설에서 dev 복귀
> plan `No changes`로 무해함 확인).

### 2.2 본 실행 네트워크 선택지 (Option A / B)

금요일 본 실행은 아래 두 구조 중 하나를 선택한다.

| 구분 | Option A — 리허설 구조 유지 | Option B — full clone(prod-like) |
| --- | --- | --- |
| ECS 배치 | public subnet + public IP | **private subnet** |
| Egress | 없음(직접 public) | **NAT Gateway** 경유 |
| EIP | 미사용 | **NAT용 EIP 소비** |
| 성격 | 빠르고 단순한 성능 검증 | 운영과 동일한 3-tier 검증 |
| tfvars | `ecs_in_private_subnets=false`, `nat_gateway_enabled=false` | `ecs_in_private_subnets=true`, `nat_gateway_enabled=true` |

> **Option B 선택 시 반드시 재확인**: EIP 여유(리전 기본 5개, dev/prod NAT가 이미 점유),
> NAT Gateway 생성 여유, Fargate On-Demand/Spot vCPU 쿼터, RDS 인스턴스 생성 여유.
> (§3 실행 전 점검의 쿼터 명령으로 확인)

## 3. 실행 전 점검

```bash
aws sts get-caller-identity --profile bada-team
```

```bash
aws service-quotas get-service-quota \
  --region ap-northeast-2 \
  --service-code fargate \
  --quota-code L-3032A538 \
  --profile bada-team
```

```bash
aws service-quotas get-service-quota \
  --region ap-northeast-2 \
  --service-code fargate \
  --quota-code L-36FBB829 \
  --profile bada-team
```

확인 항목:

- Fargate On-Demand vCPU 한도
- Fargate Spot vCPU 한도
- NAT Gateway/EIP 사용량
- RDS 인스턴스 생성 여유
- SQS/DLQ 대상이 `perf`인지 여부
- 테스트에 사용할 계정, 토큰, case 데이터
- CloudWatch/Grafana 대시보드 접근 경로
- 종료 절차 담당자

## 4. 권장 실행 흐름

### 4.1 기립 리허설

목적은 `perf` 환경이 정상적으로 생성·삭제되는지 확인하는 것이다.

```bash
cd infra
terraform init -reconfigure -backend-config=backends/perf.hcl
terraform plan -var-file=env/perf.tfvars
terraform apply -var-file=env/perf.tfvars
```

검증:

```bash
curl -fsS "$PERF_API_URL/health"
aws ecs describe-services \
  --region ap-northeast-2 \
  --cluster bada-perf-cluster \
  --services bada-perf-backend bada-perf-worker \
  --profile bada-team
```

리허설 후 정리:

```bash
terraform destroy -var-file=env/perf.tfvars
```

정리 중 ALB access log 버킷이 비어 있지 않아 삭제가 멈추는 경우, 해당 환경의 ALB log bucket만 비운 뒤 destroy를 재실행한다.

```bash
aws s3 rm s3://bada-perf-alb-logs --recursive --profile bada-team
terraform destroy -var-file=env/perf.tfvars
```

### 4.1.1 2026-07-06 기립 리허설 결과

2026-07-06에 `perf` backend state(`bada/perf/terraform.tfstate`)와 `bada-perf-*` prefix 기준으로 최소 스케일 기립 리허설을 수행했다.

검증 결과:

- Terraform plan: 신규 `perf` 리소스만 생성 대상으로 확인
- Terraform apply: `bada-perf-cluster`, Backend/Worker ECS, RDS, SQS/DLQ, S3, ALB, WAF, ACM, Route53, Secrets Manager, CloudWatch 리소스 생성 확인
- API smoke: `https://api.perf.badasoft.com/health` → HTTP 200 (⚠️ 7/6 리허설 기록. 이후 DNS 위임 끊김 확인 → 본 실험은 `http://<perf-alb-dns>/health` 200으로 수행)
- ECS: Backend/Worker desired 1, running 1 상태 확인
- SQS: main queue visible 0, in-flight 0 확인
- Terraform destroy: `perf` state empty, RDS/S3 삭제 확인, ECS cluster는 `INACTIVE` 상태 확인
- dev backend 복귀 후 Terraform plan: `No changes`

리허설 중 발견 및 보완:

| 항목 | 원인 | 보완 |
| --- | --- | --- |
| Backend ECS Service 최초 생성 실패 | Backend service가 Target Group을 ALB listener/rule에 연결하기 전에 생성될 수 있음 | Backend service가 HTTP/HTTPS listener와 API listener rule 이후 생성되도록 의존성 보강 |
| Worker 최초 기동 실패 | Secrets Manager secret version의 `AWSCURRENT` 라벨 생성 전에 Worker task가 secret을 조회함 | Backend/Worker service가 app secret version 이후 생성되도록 의존성 보강 |
| ALB log bucket 삭제 실패 | ALB access log가 남아 있어 S3 bucket 삭제가 차단됨 | destroy 재실행 전 해당 환경의 ALB log bucket을 비우는 절차 추가 |

### 4.2 본 성능 검증

본 검증은 아래 순서로 진행한다.

1. `perf` 환경 생성
2. 기준 상태 확인
3. Backend 읽기 부하
4. Backend scale-out 부하
5. Worker SQS backlog 부하
6. 안정화 관측
7. 결과 캡처
8. 큐/데이터 정리
9. `perf` 환경 제거

대규모 확장 검증을 수행하는 경우에는 위 순서를 유지하되, 아래 단계로 확장한다.

1. `perf` 환경 scale-up 프로파일 확정
2. 1,000 VU smoke
3. 3,000 VU 본 테스트
4. 5,000~10,000 VU 한계 테스트
5. RDS/Backend/Worker 사이징 비교
6. SQS backlog 10만 건 drain 테스트
7. 장애 주입 테스트
8. 결과 표·그래프 정리
9. `terraform destroy`

세부 기준과 결과 기록 양식은 [`perf-scale-experiment.md`](./perf-scale-experiment.md)를 기준으로 한다.

## 5. 부하 시나리오

### 5.1 Smoke

```bash
k6 run -e TARGET_URL="$PERF_API_URL" -e VUS=5 -e SUSTAIN=1m load-test/k6/backend-journey.js
```

목적:

- 대상 URL과 인증/비인증 경로 확인
- 기본 error rate 확인
- Grafana/CloudWatch 지표 수집 여부 확인

### 5.2 사용자 여정 부하

```bash
k6 run \
  -e TARGET_URL="$PERF_API_URL" \
  -e VUS=300 \
  -e SUSTAIN=15m \
  load-test/k6/backend-journey.js
```

확장 예시:

```bash
k6 run \
  -e TARGET_URL="$PERF_API_URL" \
  -e TOKEN="$TOKEN" \
  -e VUS=500 \
  -e SUSTAIN=20m \
  load-test/k6/backend-journey.js
```

관측:

- p95 latency
- http_req_failed
- RPS
- Backend CPU/Memory
- ALB target response time / 5xx
- RDS CPU / DatabaseConnections

### 5.3 Backend scale-out 부하

```bash
k6 run \
  -e TARGET_URL="$PERF_API_URL" \
  -e MODE=latency \
  -e RATE=300 \
  -e MAX_VUS=1000 \
  -e SUSTAIN=20m \
  load-test/k6/backend-autoscaling.js
```

필요 시 단계적으로 올린다.

| 단계 | RATE | MAX_VUS | 유지 시간 |
| --- | ---: | ---: | --- |
| 1 | 100 | 300 | 10m |
| 2 | 300 | 1000 | 20m |
| 3 | 500 | 1200 | 20m |

관측:

- Backend CPU 70% 이상 유지 여부
- Backend RunningTaskCount/DesiredCount 증가
- scale-out 감지 시각
- 신규 task healthy 전환 시각
- p95 상승 후 회복 여부

### 5.4 Worker SQS backlog 부하

> **1차 실행 결과(2026-07-07)**: `--count 50000`으로 수행 → 3.7초에 50,000건 투입, Worker **2→20 자동 확장**, DLQ 0. 아래 `--count 100000`은 후속 확대 목표다("100,000건 완료"로 기록하지 말 것).

`perf` 큐를 명시한다.

```bash
python load-test/sqs/fill_backlog.py \
  --queue bada-perf-analysis \
  --count 50000 \
  --workers 40 \
  --watch \
  --profile bada-team
```

확장 예시:

```bash
python load-test/sqs/fill_backlog.py \
  --queue bada-perf-analysis \
  --count 100000 \
  --workers 60 \
  --watch \
  --profile bada-team
```

관측:

- ApproximateNumberOfMessagesVisible
- ApproximateNumberOfMessagesNotVisible
- ApproximateAgeOfOldestMessage
- Worker RunningTaskCount/DesiredCount
- Worker scale-out 활동
- drain 완료 시간
- DLQ 메시지 수

주의:

- bogus `case_id` 메시지는 실제 분석 처리 시간을 대표하지 않는다.
- 이 시나리오는 backlog와 Worker scale-out/drain 회복을 검증하기 위한 것이다.
- 실제 E2E 분석 latency는 유효 case를 소량으로 별도 측정한다.

## 6. 결과 기록 양식

| 항목 | 값 |
| --- | --- |
| 실행 일시 |  |
| 대상 환경 | `perf` |
| 대상 URL |  |
| Backend min/max |  |
| Worker min/max |  |
| RDS class |  |
| 테스트 종류 | Smoke / Journey / Backend scale / Worker backlog |
| VU 또는 RATE |  |
| 메시지 수 |  |
| p95 latency |  |
| error rate |  |
| peak RPS |  |
| Backend peak task count |  |
| Worker peak task count |  |
| RDS peak CPU |  |
| SQS peak visible |  |
| SQS peak oldest age |  |
| DLQ count |  |
| 주요 병목 |  |
| 개선 후보 |  |

## 7. 종료 절차

1. k6/SQS producer 중지
2. SQS depth 확인
3. 필요 시 `perf` 큐 purge
4. ECS service desired count 안정화 확인
5. Grafana/CloudWatch 캡처 저장
6. 결과표 작성
7. Terraform destroy
8. 남은 리소스 확인

```bash
aws sqs get-queue-attributes \
  --queue-url "$PERF_QUEUE_URL" \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
  --region ap-northeast-2 \
  --profile bada-team
```

```bash
cd infra
terraform init -reconfigure -backend-config=backends/perf.hcl
terraform destroy -var-file=env/perf.tfvars
```

삭제 후 확인:

```bash
aws ecs describe-clusters \
  --clusters bada-perf-cluster \
  --region ap-northeast-2 \
  --profile bada-team
```

```bash
aws rds describe-db-instances \
  --db-instance-identifier bada-perf-postgres \
  --region ap-northeast-2 \
  --profile bada-team
```

## 8. 판정 기준

| 구분 | 성공 기준 |
| --- | --- |
| Backend 안정성 | 주요 테스트 구간에서 5xx가 통제 가능한 수준이며 p95 회복 구간이 확인됨 |
| Backend Auto Scaling | 부하 증가 후 Desired/Running task 증가가 확인됨 |
| Worker Auto Scaling | backlog 증가 후 Worker task 증가와 drain 회복이 확인됨 |
| RDS | CPU/Connection이 포화 상태로 장시간 고착되지 않음 |
| SQS/DLQ | 테스트 종료 후 visible/in-flight가 정리되고 DLQ가 통제됨 |
| 정리 | `perf` 임시 리소스가 제거됨 |

## 9. 보고서에 포함할 그래프

- Backend CPU vs Backend task count
- p95 latency vs request rate
- ALB 5xx / target response time
- RDS CPU / DatabaseConnections
- SQS visible / oldest age
- Worker task count
- Worker drain time
- Scale-out activity timeline


---

## 10. perf-medium 단계 실행 결과 (2026-07-07)

perf-small 대비 Backend task를 **1 vCPU / 2GB, min 4 / max 30**, RDS **db.m6g.large**로 상향(`perf.tfvars`만 수정, plan `1 add / 3 change / 1 destroy`, dev/prod 변경 0).

- ⚠️ Backend 서비스 `ignore_changes=[task_definition]` → apply 후 `aws ecs update-service --task-definition bada-perf-backend --force-new-deployment`로 새 task def(1vCPU) 반영 필요.
- 1,000 VU journey 재검증: 평균 RPS 23.9→697, p95 60s→96ms, Backend CPU 100%→59% (**CPU 병목 해소**).
- 3,000 VU latency(RATE=300, `/community/boards`): 실패율 83.56%이나 대부분 **429(앱 IP rate limit)** — Backend CPU 16%. 자세한 원인은 `perf-scale-experiment.md §14`.

**중요**: 비면제 엔드포인트 부하는 앱 IP rate limit(`_LIMIT=300/60s`, 면제 `/health`·`/version`·`/health/db`)에 먼저 걸린다. 단일 IP 부하로는 이 이상 유효 부하를 못 만드므로, 한계 테스트는 **분산 소스 IP(분산 k6 runner)** 선행이 필요하다.
