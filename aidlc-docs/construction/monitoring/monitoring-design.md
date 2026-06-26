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
