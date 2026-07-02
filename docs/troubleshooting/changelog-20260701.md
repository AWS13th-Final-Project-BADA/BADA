# 변경 이력 — 2026-07-01

> 작업자: 김재현, 이동규, 허성우
> 주요 작업: STT 파이프라인 완성, 성능 최적화, 다국어 분석, Grafana 수정, Worker 메트릭

---

## 음성 전사(STT) → entities 구조화 파이프라인 완성 (PR #172)

### 문제
- Amazon Transcribe 전사는 성공(ocr_text 채워짐)하지만 extracted_entities가 비어있음
- 분석/PDF에 음성 증거 데이터가 반영 안 됨

### 수정
- `handlers/analysis.py`에 `_extract_audio_entities()` 추가
- 분석 실행 시: audio (전사 완료 + entities 없음) → `_structure_text()`로 병렬 구조화
- 음성에서 추출 가능: 금액, 시급, 공제, 날짜, 발화 분류(utterances)

### 검증 결과
- 시나리오 2 (불법 공제): hw=10030, deds=2(기숙사비+식비), utts=9 ✅
- 시나리오 1 (임금 지급): hw=10030, expected=120,360원(시급×12시간) ✅
- 시나리오 4 (퇴직금): mw=2096000, utts=13 ✅

---

## 타임라인 날짜 파싱 에러 수정 (PR #177)

### 문제
- LLM이 `event_date`에 "12월 11일" 같은 한국어 날짜 반환
- PostgreSQL DATE 컬럼 파싱 실패 → 분석 handler 전체 에러 → SQS 무한 재시도

### 수정
- `event_date=ev.get("date")` → `event_date=_dt(ev.get("date"))` (ISO 변환 실패 시 None)

---

## Worker CPU 상향 적용 확인

- 1024 CPU (1 vCPU) + 2048 MiB 정상 적용 확인
- PDF 생성 시간: **50초 → 15초** (실측)
- 분석 파이프라인 전체 (10건): ~96초

---

## 분석 결과 다국어 지원 (PR #178, #179)

### 하드코딩 한국어 → i18n 전환 (PR #178)
- "PDF 생성 중..." → `t("analysis.pdfGenerating")`
- "날짜 미확인" → `t("analysis.dateUnknown")`
- "입금 자료 확인" / "자료 확인" → `t("analysis.paymentConfirm")` / `t("analysis.documentConfirm")`
- 5개 언어(ko/en/vi/km/ja) 추가

### LLM 응답 언어 전달 (PR #179)
- FE `lang=ko` 하드코딩 → 사용자 `locale` 변수로 전달
- Backend → SQS message에 `lang` 포함 → Worker `target_lang`으로 사용
- narrative/timeline/missing이 해당 언어로 생성됨
- PDF 생성에도 동일 lang 반영

---

## 분석 완료 후 "분석 실행" 버튼 제거 (PR #171)

- 이미 완료된 상태에서 분석 실행 버튼 → 사용자 혼란
- "자료 보강" 버튼만 남김

---

## 사건 상세 분석 완료 상태 표시 (PR #174)

- `status=completed`인 사건: "업로드한 자료" → "분석 결과" 버튼으로 전환
- 아이콘 변경 (analytics → fact-check)

---

## 사건 목록 뒤로가기 시 갱신 (PR #176)

- `useEffect` → `useFocusEffect`로 변경
- 사건 생성 후 뒤로가기 시 목록 자동 갱신

---

## 일괄 업로드 시 화면 깜빡임 수정 (PR #170)

- 매 건 완료마다 `setFiles` → 전부 끝난 후 한 번에 업데이트
- 업로드 중 계단식 움직임 제거

---

## Grafana Infrastructure 대시보드 수정 (PR #180)

### 문제
- Backend/Worker CPU/Memory 전부 No Data

### 원인
- CloudWatch 네임스페이스 불일치: `AWS/ECS` → 실제 데이터는 `ECS/ContainerInsights`
- 메트릭명 불일치: `CPUUtilization` → 실제는 `CpuUtilized`
- 템플릿 변수 미치환

### 수정
- namespace: `ECS/ContainerInsights`
- metric: `CpuUtilized` / `MemoryUtilized`
- dimensions: 하드코딩 (`bada-dev-cluster`, `bada-dev-backend/worker`)

### 현재 상태
- Grafana Docker 이미지 재빌드 필요 (인프라 담당)
- 또는 Grafana UI에서 직접 패널 쿼리 수정으로 즉시 해결 가능

---

## Worker Prometheus 비즈니스 메트릭 추가 (PR #181)

Worker에 `prometheus_client` + `:9090/metrics` HTTP 서버 도입.

### 계측 항목

| 메트릭 | 설명 |
|--------|------|
| `worker_sqs_messages_total` | SQS 메시지 처리 (task_type/status) |
| `worker_sqs_processing_seconds` | 메시지당 처리 소요시간 |
| `worker_bedrock_calls_total` | Bedrock 호출 횟수 (purpose/status) |
| `worker_bedrock_latency_seconds` | Bedrock 레이턴시 |
| `worker_ocr_processed_total` | OCR 처리 건수 |
| `worker_ocr_batch_size` | 병렬 배치 크기 |
| `worker_stt_processed_total` | STT 전사 건수 |
| `worker_stt_latency_seconds` | STT 소요시간 |
| `worker_pdf_generated_total` | PDF 생성 건수 |
| `worker_pdf_latency_seconds` | PDF 생성 소요시간 |
| `worker_analysis_total` | 분석 전체 건수 |
| `worker_analysis_duration_seconds` | 분석 전체 소요시간 |
| `worker_idle` | Worker 유휴 상태 (1=대기, 0=처리중) |

### 2026-07-02 인프라 적용 결과

- Prometheus scrape config에 Worker 타겟 추가 완료
  - 대상: Cloud Map `worker.bada-dev.local:9090`
  - 방식: `dns_sd_configs` A 레코드 + port `9090`
- Worker Task Definition에 9090 portMapping 추가 완료
  - 적용 Task Definition: `bada-dev-worker:55`
  - 인프라 수동 전환 기준 `:54`에서 기존 서비스 이미지(`8f46afda7af0`)를 유지했고, 이후 Worker CD가 새 이미지 `33ba8f1ff653` 기반 `:55`로 배포하면서 9090 portMapping을 유지
- Monitoring SG → ECS SG 9090 ingress 허용 완료
- Cloud Map Worker service discovery 생성 및 ECS Worker Service 연결 완료
- 검증:
  - `terraform fmt`, `terraform validate` 통과
  - `terraform apply` 완료 후 후속 `terraform plan` = `No changes`
  - Worker 로그에서 `Prometheus 메트릭 서버 시작: port=9090` 확인
  - Prometheus `bada-dev-prometheus:3`, Grafana `bada-dev-grafana:10`, Worker `bada-dev-worker:55` 안정화 확인

---

## STT 테스트 스크립트 작성 (PR #175)

- `docs/test/stt-test-scripts.md`
- 3개 시나리오 (임금지급약속 / 불법공제 / 수당미지급)
- 각 스크립트에 hourly_wage, work_days, overtime_hours, deductions 등 핵심 엔티티 포함
- 녹음 가이드 + 검증 체크리스트

---

## 성능 개선 최종 결과 (증거 12건 기준)

| 단계 | 6/30 (개선 전) | 7/1 (최종) | 단축률 |
|------|---------------|-----------|--------|
| OCR | 240초 (순차) | ~25초 (병렬 50) | 90% |
| 분석 LLM | ~5초 | ~5초 | — |
| PDF 생성 | ~50초 | ~15초 (1 vCPU) | 70% |
| **합계** | **~295초** | **~45초** | **85%** |

---

## 인프라 요청 잔여 사항

| 항목 | 상태 |
|------|------|
| Grafana dashboard provisioning 반영 | 완료 (`bada-dev-grafana:10`) |
| Prometheus에 Worker `:9090` 타겟 추가 | 완료 (`worker.bada-dev.local:9090`) |
| Worker task definition portMappings 9090 | 완료 (`bada-dev-worker:55`) |
| Grafana UI 패널 쿼리 수동 수정 | 불필요: Terraform/dashboard JSON 경로로 영구 반영 |
