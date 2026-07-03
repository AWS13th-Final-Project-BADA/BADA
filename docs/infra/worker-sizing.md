# Worker 사이징 산정 근거 (ECS Task 스펙 + OCR 병렬 동시성)

> 작성일: 2026-06-30
> 대상: bada-dev-worker (ECS Fargate) / Worker `_handle_ocr`(consumer.py)
> 비고: 기존 Worker Task 스펙 산정 문서와 OCR 병렬 동시성 산정 문서를 하나로 통합했다.

---

## 1. Worker ECS Task 스펙 산정

### 변경 이력

| 시점 | CPU (vCPU) | Memory (MiB) | 사유 |
|------|-----------|-------------|------|
| 초기 (6/19~) | 256 (0.25) | 512 | 최소 스펙으로 MVP 시작 |
| 변경 (6/30~) | 1024 (1.0) | 2048 | PDF 생성 성능 병목 해소 |

### Fargate 스펙 범위 참고

| CPU (vCPU) | 메모리 범위 | 일반 용도 |
|---|---|---|
| 0.25 | 0.5~2 GB | 경량 사이드카, 최소 테스트 |
| 0.5 | 1~4 GB | 가벼운 API 서버 |
| 1 | 2~8 GB | 일반 워크로드, 백그라운드 처리 |
| 2 | 4~16 GB | 중량 배치, 이미지/동영상 처리 |
| 4 | 8~30 GB | ML 추론, 대용량 데이터 처리 |

### Worker 작업 구성 분석

Worker가 처리하는 작업(증거 1건 기준):

| 단계 | 소요 시간 | 특성 | CPU 영향 |
|------|----------|------|---------|
| 1차 Bedrock Vision (텍스트 추출) | ~20초 | I/O-bound (API 대기) | 없음 |
| 2차 Bedrock Text (entities 구조화) | ~20초 | I/O-bound (API 대기) | 없음 |
| 분석 LLM 호출 | ~5초 | I/O-bound (API 대기) | 없음 |
| PDF 생성 (WeasyPrint + 한글 폰트) | ~50초 | **CPU-bound** | **비례 단축** |
| **합계** | **~95초** | | |

핵심: **전체 95초 중 CPU가 영향을 주는 구간은 PDF 생성(~50초)뿐.**
나머지 ~45초는 Bedrock API 응답 대기로, CPU를 아무리 올려도 줄어들지 않음.

### 스펙별 예상 성능

| CPU | PDF 생성 예상 | 전체 예상 | 비용 (desired=1, 2주) |
|-----|-------------|----------|---------------------|
| 0.25 vCPU | ~50초 | ~95초 | 기준 |
| 0.5 vCPU | ~25초 | ~70초 | +$3 |
| **1 vCPU** | **~12-15초** | **~60초** | **+$8** |
| 2 vCPU | ~8-10초 | ~55초 | +$20 |

### 의사결정: 1 vCPU 선택 근거

1. **병목 구간(PDF)의 CPU 비례 효과가 가장 큰 구간**: 0.25 → 1 vCPU에서 50초 → 15초로 70% 단축
2. **수확 체감**: 1 → 2 vCPU에서는 15초 → 10초 (33% 단축)이지만 비용은 2배. 가성비 떨어짐
3. **I/O-bound 구간은 불변**: Bedrock 대기 45초는 CPU와 무관하므로 추가 상향 효과 제한적
4. **비용**: desired=1 기준 약 $8/2주 추가. 총 예산($1,500) 대비 무시 가능

결론: **1 vCPU가 가성비 최적점.** 이 이상은 투자 대비 효과 미미.

> **참고**: AWS Fargate 공식 문서에는 워크로드별 권장 스펙이 없음.
> 이 결정은 실측 프로파일링(0.25 vCPU에서 PDF 생성 50초, CPU utilization ~100%) 기반이며,
> CPU-bound 구간과 I/O-bound 구간을 분리하여 비용 대비 효과가 가장 큰 지점을 산출한 것.

### 추가 성능 개선 방안 (CPU 외)

| 방안 | 효과 | 복잡도 | 상태 |
|------|------|--------|------|
| 1-pass OCR 복귀 | Bedrock 호출 2→1회, ~20초 절약 | 낮음 | 적용 완료 (PR #152) |
| 증거 병렬 OCR | N건 순차→동시 처리 | 중간 | 적용 완료 (PR #157, 아래 2장) |
| 구조화에 Haiku 모델 사용 | 2차 호출 20초→5초 | 낮음 | 미착수 |
| PDF 경량 폰트 전환 | 폰트 임베딩 시간 단축 | 중간 | 미착수 |

### 산정 방법론 (자체 개발 서비스 기준)

상용 SW처럼 "일일 N건 처리 기준 CPU X 이상" 같은 벤더 문서가 없으므로, 아래 절차로 산정:

1. **작업 프로파일링**: 각 단계의 소요 시간과 리소스 특성(CPU-bound vs I/O-bound) 분류
2. **SLA 목표 설정**: "사용자 업로드 후 2분 이내 결과 표시" 등 목표 정의
3. **병목 식별**: CPU 올려서 줄어드는 구간과 줄어들지 않는 구간 분리
4. **단계별 스펙 테스트**: 0.25 → 0.5 → 1 → 2 순으로 올려가며 실측
5. **수확 체감점 찾기**: 비용 대비 시간 단축 효과가 30% 미만이면 중단
6. **CloudWatch 모니터링**: CPU/Memory utilization 80% 이상이면 상향, 30% 이하면 하향 검토

---

## 2. OCR 병렬 처리 동시성(max_workers) 산정

### 결론

`max_workers = min(len(evidences), 50)`

증거 건수가 50 이하면 전부 동시, 50 초과면 50개씩 배치.

### Bedrock API Quota (실측)

AWS Service Quotas에서 확인한 우리 계정(`165749212250`) ap-northeast-2 기준.
사용 모델: `global.anthropic.claude-sonnet-4-6` (Cross-region inference)

| 항목 | Quota | 비고 |
|------|-------|------|
| **Cross-region requests/min (Sonnet 4.6)** | **10,000 RPM** | 우리 모델에 적용되는 실제 quota |
| Cross-region tokens/min (Sonnet 4.6) | 6,000,000 | 토큰 제한 |
| On-demand Claude 3.5 Sonnet | 50 RPM | 참고: 이전 모델. 우리는 해당 없음 |

> 주의: `global.*` prefix = cross-region inference 모드. on-demand quota가 아닌 cross-region quota가 적용됨.

### 산출 과정

1건의 분석에서 발생하는 Bedrock 호출:

| 단계 | 호출 수 | 비고 |
|------|---------|------|
| OCR (증거 N건) | N회 | 1-pass, 증거당 1회 |
| 분석 LLM | 1회 | analyze_case |
| PDF 생성 중 LLM | 0회 | CPU-only |
| **합계** | **N + 1** | |

**12건 증거 시나리오**: 총 Bedrock 호출 12(OCR) + 1(분석) = 13회 → 13 requests/min. quota 대비 여유.

**max_workers 후보 비교**:

| max_workers | 피크 메모리 | 가용 대비 사용 | 마진 | 판단 |
|---|---|---|---|---|
| 10 | ~120 MB | 7% | 93% | 보수적 |
| 20 | ~240 MB | 13% | 87% | 안전 |
| **50** | **~600 MB** | **33%** | **67%** | **채택 — 현실적 상한, 마진 충분** |
| 90 | ~1080 MB | 60% | 40% | 허용 가능 (마진 최소선) |
| 100 | ~1200 MB | 67% | 33% | OOM 위험 |

산출 기준:
- 가용 메모리: 2048 MiB - 기본 프로세스 ~200 MB = **~1800 MB**
- 1건당 피크 메모리: ~12 MB (원본 이미지 ~5MB + base64 인코딩 ~7MB)
- 마진 기준: **40% 이상** 확보 (가용의 60%까지 사용 허용)
- 60% 상한 = 1080 MB ÷ 12 MB = 90건이 이론적 최대
- **50건 채택**: 마진 67%로 여유 확보 + 현실적 사용 패턴 커버

### 리소스 제약 확인

- **메모리**: Worker 2048 MiB. 이미지 1건 ~3-5 MB(S3 읽기). 병렬 로딩 + base64 인코딩이 실제 상한 요인 → OOM 방지 목적.
- **CPU**: Worker 1 vCPU. OCR 스레드는 I/O-bound(Bedrock API 대기 ~20초)로 CPU 경합 없음 → 여유.
- **네트워크**: Bedrock HTTPS 호출(이미지 base64 payload). Fargate burst 가능 → 여유.

### 안전 마진 요약

| 제약 | 한도 | 50건 동시 사용량 | 마진 |
|------|------|-----------------|------|
| Bedrock RPM (cross-region, Sonnet 4.6) | 10,000/min | ~50/min | **99.5% 여유** |
| Worker Memory | 2048 MiB | ~600 MB (피크) | **67% 여유** |
| Worker CPU | 1 vCPU | ~0.1 vCPU (I/O-bound) | **90% 여유** |

> API quota는 사실상 제한이 아님. max_workers를 제한하는 이유는 quota보다는
> **메모리**(이미지 동시 로딩 + base64 인코딩)와 **OOM 방지**가 목적.

---

## 모니터링 지표

적용 후 CloudWatch에서 확인할 항목:
- `ECS/CPUUtilization` (Worker service): PDF 생성 중 피크 확인
- `ECS/MemoryUtilization` (Worker service): 폰트 로딩 / OCR 병렬 시 메모리 사용량
- Worker 로그: `extract_ocr 완료` 시간 (12건 기준 이전 240초 → 목표 30초 이내)
- Bedrock `ThrottlingException` 발생 여부: 없어야 정상
- SQS `ApproximateAgeOfOldestMessage`: 처리 대기 시간 단축 확인
