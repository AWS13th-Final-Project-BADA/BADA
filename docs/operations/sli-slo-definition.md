# BADA SLI/SLO 정의

> 서비스 수준 지표(SLI)와 목표(SLO)를 정의하여 운영 품질을 정량적으로 관리한다.
> 측정 기간: 7일 롤링 윈도우. 데모 기간(~7/10) 기준.

---

## SLI 정의

| SLI | 측정 방법 | Prometheus 쿼리 |
|-----|----------|----------------|
| **가용성** | 2xx+3xx 응답 비율 | `sum(rate(http_requests_total{status=~"2..\\|3.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| **API 레이턴시 (p95)** | 요청 응답 시간 95번째 백분위 | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` |
| **분석 성공률** | 분석 완료 / 분석 시도 | `sum(bada_analysis_runs_total{status="success"}) / sum(bada_analysis_runs_total)` |
| **분석 소요 시간 (p95)** | 분석 파이프라인 95번째 백분위 | `histogram_quantile(0.95, rate(bada_analysis_duration_seconds_bucket[5m]))` |
| **Worker 처리율** | SQS 메시지 성공 처리 비율 | `sum(bada_sqs_messages_processed_total{status="success"}) / sum(bada_sqs_messages_processed_total)` |

---

## SLO 목표

| SLI | SLO | 에러 버짓 (7일) | 근거 |
|-----|-----|----------------|------|
| 가용성 | ≥ 99% | ~1시간 41분 다운 허용 | 데모 환경 단일 인스턴스 감안 |
| API 레이턴시 (p95) | ≤ 500ms | — | CRUD API 기준, AI 호출 제외 |
| 분석 성공률 | ≥ 95% | 20건 중 1건 실패 허용 | Bedrock 쓰로틀/타임아웃 감안 |
| 분석 소요 시간 (p95) | ≤ 5분 | — | OCR+규칙+번역+요약 전체 |
| Worker 처리율 | ≥ 98% | — | DLQ 이동 = 실패 |

---

## 에러 버짓 정책

| 버짓 소진율 | 대응 |
|------------|------|
| < 50% | 정상 운영, 기능 개발 진행 |
| 50~80% | 신규 배포 시 추가 검증 수행 |
| 80~100% | feature freeze, 안정화 집중 |
| 100% 초과 | 긴급 대응, 롤백 검토 |

---

## 측정 대시보드

Grafana에 다음 패널 추가 예정:

1. **SLO 현황 게이지** — 각 SLI의 현재 달성률
2. **에러 버짓 소진 그래프** — 7일 기준 남은 버짓 %
3. **비즈니스 KPI** — 사건 생성 수, 분석 완료 수, PDF 생성 수 (일별)

---

## Alert 매핑

| SLI 위반 | Alert 심각도 | 대응 시간 |
|---------|------------|----------|
| 가용성 < 95% (5분간) | 🔴 Critical | 즉시 |
| 가용성 < 99% (1시간) | 🟡 Warning | 30분 |
| 분석 성공률 < 90% | 🔴 Critical | 즉시 |
| API p95 > 2초 | 🟡 Warning | 1시간 |
| Worker 처리율 < 90% | 🔴 Critical | 즉시 |

---

## 참고

- 현재 Auto Scaling 미적용 → 가용성 SLO는 단일 태스크 기준
- Phase 3 (Auto Scaling + Multi-AZ) 적용 후 SLO 상향 검토: 99% → 99.9%
- Bedrock 쓰로틀은 외부 의존성이므로 분석 SLO에서 감안
