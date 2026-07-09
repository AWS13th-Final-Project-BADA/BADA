# 모니터링 설계 — Prometheus + Grafana (ECS Fargate)

## 개요

BADA 프로덕션 환경에 오픈소스 모니터링 스택을 구축한다.
현업 표준인 **Prometheus(메트릭 수집) + Grafana(시각화/알림)** 조합으로 구성.

## 아키텍처

```
                         monitor.badasoft.com
                                │
                                ▼
                    ┌───────────────────────┐
                    │   ALB (HTTPS/443)     │
                    │   호스트 라우팅         │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   Grafana     │
                    │  (ECS, :3000) │
                    └───────┬───────┘
                            │ 데이터소스
                  ┌─────────┼─────────┐
                  ▼         ▼         ▼
          ┌────────────┐ ┌────────────┐ ┌──────────┐
          │ Prometheus │ │ CloudWatch │ │  Loki    │
          │ (ECS,:9090)│ │ datasource │ │ (선택)   │
          └─────┬──────┘ └────────────┘ └──────────┘
                │ scrape
                ▼
       api.badasoft.com/metrics
```

## 컴포넌트

### 1. Prometheus (ECS Fargate Task)
- **역할**: 메트릭 수집 (scrape)
- **포트**: 9090
- **스토리지**: Fargate 임시 볼륨, 3일 보존
  - Prometheus TSDB는 NFS/EFS를 지원하지 않으므로 로컬 볼륨을 사용한다.
  - 태스크 교체 시 과거 메트릭은 초기화되며, 장기 보존이 필요하면 Amazon Managed Service for Prometheus를 검토한다.
- **scrape 대상**:
  - `https://api.badasoft.com/metrics` (FastAPI + prometheus_client)
  - Prometheus 자체
- **설정 배포**: ECS 초기화 컨테이너가 저장소의 `prometheus.yml`을 공유 설정 볼륨에 기록
- **내부 접근**: Cloud Map `prometheus.bada-dev.local:9090`
- **Worker 메트릭**: exporter 구현 후 별도 target으로 추가

### 2. Grafana (ECS Fargate Task)
- **역할**: 대시보드 시각화 + 알림
- **포트**: 3000
- **접근**: `monitor.badasoft.com` (ALB 호스트 라우팅)
- **데이터소스**:
  - Prometheus (메트릭)
  - CloudWatch (AWS 관리형 메트릭: ALB, RDS, SQS, ECS)
- **인증**: Grafana 자체 로그인 (admin 계정)
- **관리자 비밀번호**: Terraform 자동 생성 후 Secrets Manager `bada-dev/grafana-admin-password`에 저장
- **스토리지**: EFS (SQLite DB와 사용자 설정 영속화)
- **프로비저닝**: 초기화 컨테이너가 Prometheus/CloudWatch 데이터소스와 BADA Overview 대시보드를 자동 배치

### 3. Backend /metrics 엔드포인트
- **라이브러리**: `prometheus_client` (Python)
- **메트릭**:
  - `http_requests_total` (method, path, status)
  - `http_request_duration_seconds` (histogram)
  - `active_cases_total`
  - `analysis_runs_total` (status: success/failed)
  - `ocr_requests_total` (provider, status)

### 4. Worker 메트릭
- **메트릭**:
  - `worker_messages_processed_total` (handler, status)
  - `worker_message_duration_seconds` (histogram)
  - `worker_sqs_messages_in_flight`

## 대시보드 계획

| 대시보드 | 패널 |
|----------|------|
| **Overview** | 총 요청수, 에러율, P95 응답시간, 활성 사건 수 |
| **Backend** | HTTP 메서드별 요청, 상태코드 분포, 응답 지연 히스토그램 |
| **Worker** | 메시지 처리량, 처리 시간, 실패율, SQS 깊이 |
| **Infrastructure** | ECS CPU/메모리, RDS 커넥션/IOPS, ALB 5xx, SQS 메시지 수 |

## 인프라 리소스 (Terraform)

| 리소스 | 용도 |
|--------|------|
| EFS 파일시스템 | Grafana 데이터 영속화 |
| ECS Task Definition (Prometheus) | prom/prometheus 이미지 |
| ECS Task Definition (Grafana) | grafana/grafana-oss 이미지 |
| ECS 초기화 컨테이너 | 저장소의 설정 파일을 공유 볼륨에 배치 |
| Cloud Map Private DNS | Grafana → Prometheus 내부 통신 |
| ECS Service (Prometheus) | desired=1 |
| ECS Service (Grafana) | desired=1 |
| ALB Target Group (Grafana) | 헬스체크 /api/health |
| ALB Listener Rule | monitor.badasoft.com → Grafana TG |
| Route 53 A 레코드 | monitor.badasoft.com → ALB |
| Security Group | ALB→Grafana, Grafana→Prometheus, ECS→EFS 최소 포트 허용 |
| Monitoring Task Role | CloudWatch/Logs/EC2 태그 조회 전용 권한 |

## 비용 예상 (추가)

| 항목 | 월 비용 |
|------|---------|
| ECS Fargate (Prometheus 0.25vCPU/512MB) | ~$8 |
| ECS Fargate (Grafana 0.25vCPU/512MB) | ~$8 |
| EFS (1GB 미만) | ~$0.30 |
| **합계** | **~$16/월** |

## 구현 순서

1. Backend에 `/metrics` 엔드포인트 추가 (prometheus_client)
2. Prometheus 설정 파일 (prometheus.yml) 작성
3. Terraform: Prometheus ECS + Grafana/EFS + Cloud Map + ALB 라우팅
4. Grafana 데이터소스 설정 (Prometheus + CloudWatch)
5. 대시보드 JSON 프로비저닝
6. 검증: monitor.badasoft.com 접속 확인

## 운영 및 검증

```bash
cd infra
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars

aws ecs describe-services \
  --cluster bada-dev-cluster \
  --services bada-dev-prometheus bada-dev-grafana

curl -fsS https://monitor.badasoft.com/api/health
```

Grafana 로그인 계정은 `admin`이며 비밀번호는 필요할 때만 조회한다.

```bash
aws secretsmanager get-secret-value \
  --secret-id bada-dev/grafana-admin-password \
  --query SecretString \
  --output text
```

### GPS 체인 해시 무결성

**파일**: `backend/app/routers/gps.py`

| 엔드포인트 | 설명 |
|-----------|------|
| `POST /cases/{id}/gps/ping` | 핑 저장 시 `chain_hash` 자동 생성 및 체인 연결 |
| `GET /cases/{id}/gps/verify` | 체인 연속성 검증 — 중간 조작 탐지 |
| `GET /cases/{id}/gps/summary` | 일별 요약 + 전체 SHA-256 무결성 해시 |

체인 구조: `SHA-256(prev_hash | ts | lat | lng | status)` — 중간 행 조작 시 이후 모든 hash 불일치로 탐지됨.

완료 기준:
- [x] 핑 저장 시 chain_hash 생성
- [x] /verify 엔드포인트 — 체인 연속성 검증
- [x] 중간 조작 탐지 테스트 (`tests/test_gps_chain.py`) 통과



- Prometheus와 Grafana ECS Service가 각각 `desired=1`, `running=1`, `rollout=COMPLETED`
- Grafana Target Group `healthy`
- `/api/health` HTTP 200
- Prometheus datasource health `OK`
- `prometheus`, `bada-backend` target 모두 `UP`
- BADA Overview 대시보드 자동 생성
- 후속 Terraform plan `No changes`


---

## 구현 현황 (2026-06-25)

### Alert Rule (Grafana Provisioning)

**파일**: `monitoring/grafana/provisioning/alerting/rules.yml`

| ID | Rule | 조건 | 심각도 |
|----|------|------|--------|
| G1 | 에러율 급증 | 5xx > 5% (5분) | critical |
| G2 | 응답 지연 P95 | > 3초 (5분) | warning |
| G3 | 트래픽 제로 | 0건 (10분) | critical |
| G4 | Worker 실패율 | > 10% (5분) | warning |
| G5 | Worker 처리 지연 | P95 > 60초 | warning |
| G6 | RDS 커넥션 포화 | ≥ 80 | critical |
| G7 | 분석 실패 연속 | 15분간 성공 0 | critical |
| G8 | OCR 실패율 | > 30% | warning |

### Contact Point

**파일**: `monitoring/grafana/provisioning/alerting/contactpoints.yml`

- Type: AWS SNS
- Topic: `bada-dev-alarm-notifications`
- 수신자: `badajoa0710@gmail.com`
- Notification Policy: folder+alertname 그룹핑, 4h 반복

### Dashboard

| 대시보드 | 패널 수 | 데이터소스 | 파일 |
|----------|---------|-----------|------|
| Overview | 8 | Prometheus | `bada-overview.json` |
| Infrastructure | 11 | CloudWatch | `bada-infrastructure.json` |
| Backend | 8 | Prometheus | `bada-backend.json` |
| Worker | 6 | Prometheus + CloudWatch | `bada-worker.json` |

### 배포 상태

- [x] Prometheus ECS running
- [x] Grafana ECS running
- [x] CloudWatch Alarm 14개 (Terraform)
- [x] Alert Rule YAML 작성 (G1~G8)
- [x] Contact Point YAML 작성 (SNS)
- [x] Dashboard JSON 4개 작성
- [ ] terraform apply (인프라 담당 실행 예정)
- [ ] Grafana UI 검증 (`docs/monitoring-alert-test-scenario.md`)

---

## 구현 현황 (2026-07-09) — 크로스 환경(prod) 관측 추가 (PR #252)

초기 설계 이후 반영된 변경:

- **Worker 메트릭 수집 완료**: 초기 설계의 "Worker 메트릭: exporter 구현 후 별도 target으로 추가" 항목이 구현됨(Cloud Map `worker.bada-dev.local:9090` scrape).
- **Alert Rule 확장**: G1~G8 → **G1~G10** (G9 가용성 SLO < 99%, G10 분석 성공률 < 90% 추가). 단일 출처는 `monitoring/grafana/provisioning/alerting/rules.yml`.
- **Grafana 대시보드 5개로 확장**: 기존 Overview / Backend / Worker / Infrastructure(4) + **`bada-prod-infrastructure.json`**(CloudWatch 기반 prod 인프라).
- **dev 스택에서 prod 크로스 환경 관측**(dev/prod가 별도 state·VPC라 dev Grafana가 prod를 못 보던 문제 해소):
  - prod backend는 공인 ALB(`api.prod.badasoft.com/metrics`)로 Prometheus 스크랩(`env="prod"` 라벨, `prod_monitoring_enabled` 토글).
  - prod ECS/RDS/ALB/SQS는 dev Grafana의 CloudWatch datasource로 조회(동일 계정·리전).
  - prod worker는 크로스-VPC Cloud Map 스크랩 불가 → CloudWatch(Container Insights)로 갈음.
- 상세/활성화 절차: `docs/operations/monitoring-guide.md` §9.
