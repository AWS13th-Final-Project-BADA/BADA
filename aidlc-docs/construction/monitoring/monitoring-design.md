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
          ┌────────────┐ ┌─────┐ ┌──────────┐
          │ Prometheus │ │ CW  │ │  Loki    │
          │ (ECS,:9090)│ │     │ │ (선택)   │
          └─────┬──────┘ └─────┘ └──────────┘
                │ scrape
        ┌───────┼───────┐
        ▼       ▼       ▼
    Backend  Worker   Grafana
    /metrics /metrics  자체 메트릭
```

## 컴포넌트

### 1. Prometheus (ECS Fargate Task)
- **역할**: 메트릭 수집 (scrape)
- **포트**: 9090
- **스토리지**: EFS 볼륨 (데이터 영속화, 15일 보존)
- **scrape 대상**:
  - Backend `/metrics` (FastAPI + prometheus_client)
  - Worker 자체 메트릭 (커스텀 exporter)
  - Prometheus 자체
- **설정**: `prometheus.yml` (EFS 또는 S3에서 로드)

### 2. Grafana (ECS Fargate Task)
- **역할**: 대시보드 시각화 + 알림
- **포트**: 3000
- **접근**: `monitor.badasoft.com` (ALB 호스트 라우팅)
- **데이터소스**:
  - Prometheus (메트릭)
  - CloudWatch (AWS 관리형 메트릭: ALB, RDS, SQS, ECS)
- **인증**: Grafana 자체 로그인 (admin 계정)
- **스토리지**: EFS (대시보드 설정 영속화)

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
| EFS 파일시스템 | Prometheus 데이터 + Grafana 설정 영속화 |
| ECS Task Definition (Prometheus) | prom/prometheus 이미지 |
| ECS Task Definition (Grafana) | grafana/grafana-oss 이미지 |
| ECS Service (Prometheus) | desired=1 |
| ECS Service (Grafana) | desired=1 |
| ALB Target Group (Grafana) | 헬스체크 /api/health |
| ALB Listener Rule | monitor.badasoft.com → Grafana TG |
| Route 53 A 레코드 | monitor.badasoft.com → ALB |
| Security Group | Prometheus←Backend/Worker scrape 허용 |

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
3. Terraform: EFS + Prometheus ECS + Grafana ECS + ALB 라우팅
4. Grafana 데이터소스 설정 (Prometheus + CloudWatch)
5. 대시보드 JSON 프로비저닝
6. 검증: monitor.badasoft.com 접속 확인
