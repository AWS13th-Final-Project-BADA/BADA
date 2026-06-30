# OCR 병렬 처리 동시성(max_workers) 산정 근거

> 작성일: 2026-06-30
> 대상: Worker `_handle_ocr` (consumer.py)

---

## 결론

`max_workers = min(len(evidences), 50)`

증거 건수가 50 이하면 전부 동시, 50 초과면 50개씩 배치.

---

## Bedrock API Quota (실측)

AWS Service Quotas에서 확인한 우리 계정(`165749212250`) ap-northeast-2 기준:

사용 모델: `global.anthropic.claude-sonnet-4-6` (Cross-region inference)

| 항목 | Quota | 비고 |
|------|-------|------|
| **Cross-region requests/min (Sonnet 4.6)** | **10,000 RPM** | 우리 모델에 적용되는 실제 quota |
| Cross-region tokens/min (Sonnet 4.6) | 6,000,000 | 토큰 제한 |
| On-demand Claude 3.5 Sonnet | 50 RPM | 참고: 이전 모델. 우리는 해당 없음 |

> 주의: `global.*` prefix = cross-region inference 모드. on-demand quota가 아닌 cross-region quota가 적용됨.

---

## 산출 과정

### 1건의 분석에서 발생하는 Bedrock 호출

| 단계 | 호출 수 | 비고 |
|------|---------|------|
| OCR (증거 N건) | N회 | 1-pass, 증거당 1회 |
| 분석 LLM | 1회 | analyze_case |
| PDF 생성 중 LLM | 0회 | CPU-only |
| **합계** | **N + 1** | |

### 12건 증거 시나리오

- 총 Bedrock 호출: 12(OCR) + 1(분석) = 13회
- 전부 1분 이내 실행 → 13 requests/min
- On-demand quota 50 RPM 대비 **26% 사용** → 여유

### max_workers=10 선택 이유

| max_workers | 피크 메모리 | 가용 대비 사용 | 마진 | 판단 |
|---|---|---|---|---|
| 10 | ~120 MB | 7% | 93% | 보수적 |
| 20 | ~240 MB | 13% | 87% | 안전 |
| **50** | **~600 MB** | **33%** | **67%** | **채택 — 현실적 상한, 마진 충분** |
| 90 | ~1080 MB | 60% | 40% | 허용 가능 (마진 최소선) |
| 100 | ~1200 MB | 67% | 33% | OOM 위험 |

### 산출 기준
- 가용 메모리: 2048 MiB - 기본 프로세스 ~200 MB = **~1800 MB**
- 1건당 피크 메모리: ~12 MB (원본 이미지 ~5MB + base64 인코딩 ~7MB)
- 마진 기준: **40% 이상** 확보 (가용의 60%까지 사용 허용)
- 60% 상한 = 1080 MB ÷ 12 MB = 90건이 이론적 최대
- **50건 채택**: 마진 67%로 여유 확보 + 현실적 사용 패턴 커버

---

## 리소스 제약 확인

### 메모리

- Worker 메모리: 2048 MiB
- 이미지 1건 메모리: ~3-5 MB (S3 읽기 → bytes)
- 10건 동시: ~50 MB → Worker 메모리의 2.5% → **여유**

### CPU

- Worker CPU: 1 vCPU (1024 units)
- OCR 스레드는 I/O-bound (Bedrock API 대기 ~20초)
- 실제 CPU 사용: S3 읽기 + JSON 파싱 = 미미
- 10 스레드가 동시에 API 대기해도 CPU 경합 없음 → **여유**

### 네트워크

- Bedrock API 호출: HTTPS, payload ~수 MB (이미지 base64)
- 10건 동시: ~50 MB 업로드 (base64 인코딩 기준)
- Fargate 네트워크: burst 가능 → **여유**

---

## 안전 마진

| 제약 | 한도 | 50건 동시 사용량 | 마진 |
|------|------|-----------------|------|
| Bedrock RPM (cross-region, Sonnet 4.6) | 10,000/min | ~50/min | **99.5% 여유** |
| Worker Memory | 2048 MiB | ~600 MB (피크) | **67% 여유** |
| Worker CPU | 1 vCPU | ~0.1 vCPU (I/O-bound) | **90% 여유** |

> API quota는 사실상 제한이 아님. max_workers를 제한하는 이유는 quota보다는
> **메모리**(이미지 동시 로딩 + base64 인코딩)와 **OOM 방지**가 목적.
> 마진 기준: 가용 메모리의 60% 이하 사용 (40% 이상 마진 확보).
> 50건 동시 시 33% 사용으로 기준 충족.

---

## 모니터링

병렬 처리 후 확인할 지표:
- CloudWatch Worker 로그: `extract_ocr 완료` 시간 (12건 기준 이전 240초 → 목표 30초 이내)
- Bedrock `ThrottlingException` 발생 여부: 없어야 정상
- SQS `ApproximateAgeOfOldestMessage`: 처리 지연 감소 확인
