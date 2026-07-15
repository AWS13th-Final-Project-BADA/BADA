# BADA 운영 고도화 검증

이 폴더는 BADA의 운영 부하, 자동 확장, 장애 복구를 실제 AWS 환경에서 검증한 팀 공유 산출물이다. 성공 수치뿐 아니라 실험 조건, 실패 원인, 결론의 한계를 함께 기록한다.

## 핵심 문서

| 문서 | 내용 |
| --- | --- |
| [성능·확장성·복원력 검증 보고서](./performance-load-test-report.md) | 1,000~10,000 VU, Backend CPU A/B, SQS·Worker 확장, 정상 업무 1,000건 E2E, RDS Multi-AZ failover를 한 문서로 정리 |
| [RTO/RPO 정의 및 복원 리허설](../rto-rpo-and-restore-rehearsal.md) | 장애 유형별 복구 목표와 Snapshot/PITR 실행 절차 |

## 대표 결과

| 검증 | 결과 | 해석 |
| --- | --- | --- |
| 최초 병목 | 1,000 VU에서 Backend CPU 100%, RDS CPU 약 7% | DB보다 Backend compute가 먼저 포화 |
| 프로파일 개선 | 전체 p95 60,007ms→96ms, 전체 RPS 23.9→697.1 | 여러 용량 변수를 함께 바꾼 프로파일 단위 결과 |
| CPU 단일 변수 A/B | 1→2 vCPU에서 CPU peak 99.75%→60.35%, 중앙 지연 741ms→235ms | CPU 포화는 완화됐지만 p95 timeout은 남음 |
| 대규모 분산 부하 | 10,000 VU large-A에서 2XX 88.39%, HTTP 5XX 4.85%, timeout 6.76% | 안정 처리 성공이 아니라 다음 연결·tail latency 병목 식별 |
| 정상 업무 E2E | case·SQS·Worker·DB·S3 PDF 각 1,000건 완료, DLQ 0 | local/mock AI 범위에서 exact-count 검증 |
| RDS Multi-AZ | 앱 관측 RTO 15.808초, HTTP 200 승인 쓰기 284건 누락 0 | 연속 read/write 표본에서 복구 시간과 승인 데이터 보존 측정 |

## 저장 원칙

- `assets/`: 보고서 해석에 직접 필요한 그래프만 보관한다.
- `evidence/`: 결론을 다시 확인할 수 있는 소형 요약 JSON만 보관한다.
- 요청별 원시 로그, 실행 스크립트, 개인 실행 일지는 팀 문서 범위에서 제외한다.
- 숫자는 조건과 한계를 함께 읽으며, `10,000 VU 안정 처리`나 `전체 RPO 0`처럼 범위를 넘어선 표현을 사용하지 않는다.
