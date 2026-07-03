# 변경 이력 — 2026-07-03

> 작업: "분석 실행" 스피너(결과 페이지 뜨기 전) 지연 분석 및 최적화
> 브랜치/PR: #230(음성 entity prefetch + timeline 병렬 + FE 폴링, 머지 완료), #232(vision 이미지 다운스케일)

---

## 배경 — 무엇이 스피너를 잡는가

"분석 실행"의 스피너는 워커가 `analyze_case`를 **AnalysisResult 저장까지** 끝내는 시간이다. PDF는 그 커밋 이후에 생성되므로 스피너에 포함되지 않는다(결과 페이지에서 "생성중"으로 표시됨).

## 실측 (CloudWatch Logs / Transcribe API / Bedrock 지표 — bada-team 계정 165749212250)

- **음성 케이스**: `analyze_case` ~35초 — 이 중 **음성 entity 구조화(Bedrock 텍스트) ≈13초**
- **OCR 케이스(1127684b, 문서 2개)**: `analyze_case` **76초**, 이 중 **OCR(vision) 0→53.7초가 지배(71%)**
  - Bedrock 지표(`global.anthropic.claude-sonnet-4-6`): **InvocationLatency 최대 53.5초**, **ClientErrors/ServerErrors = 0**
  - → throttle·재시도가 아니라 **단일 vision 호출이 입력/출력 토큰 양에 비례해 느린 것**. 동시성 쿼터 상향은 실익 없음(병렬은 정상 동작).
- **STT(Transcribe) 자체**: p50 ~15초 (업로드 시점에 수행)

## 적용한 개선

| # | 개선 | PR |
|---|------|----|
| 1 | 음성 entity 구조화를 **STT 직후(transcribe 핸들러)** 로 이동 → 분석 스피너에서 ~13초 제거 (실패 시 analyze 폴백 재시도) | #230 |
| 2 | timeline `summarize_event` **순차→ThreadPool 병렬**(순서 보존) | #230 |
| 3 | FE 분석 결과 폴링 **5초→2초** | #230 |
| 4 | Bedrock vision 전송 전 **이미지 다운스케일**(긴 변 1568px, JPEG) → 호출당 입력 토큰·지연↓ | #232 |

## 제외/판단 (근거 기록)

- **업로드 시점 OCR prefetch**(스피너에서 OCR 제거): 팀이 "업로드 시 OCR 제거(비용 절감)" 결정을 내린 부분이라 되돌리지 않음 — 제외
- **OCR 모델 경량화(Haiku 등)**: 종료 임박 시점 리스크로 제외
- **Bedrock 동시성/TPM 쿼터 상향**: throttle이 아니었으므로 실익 없음 — 제외
- 위 제외로, 정확도 영향이 가장 적은 **이미지 다운스케일(#4의 대안, 토큰 축소)** 만 적용

## 검증

- `worker` 테스트 **168 passed**
- `mobile-native` `npx tsc --noEmit` 통과
- 다운스케일 단위 확인: 4000×3000 → 1568×1176 JPEG(용량↓), 작은 이미지 원본 유지, PDF passthrough

## 후속(선택)

- 계측 공백: `metrics.py`의 `track_stt`/`track_pdf`/`ANALYSIS_DURATION`가 정의만 되고 미배선 → Grafana STT/PDF/전체 파이프라인 패널이 비어 있음. 상시 모니터링하려면 배선 필요.
- 배포 후 동일 유형 케이스로 `InvocationLatency`/`InputTokenCount` 재측정 시 다운스케일 실제 단축폭 확인 가능.
