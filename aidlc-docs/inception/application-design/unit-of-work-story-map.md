# 유닛-요구사항 매핑

## 매핑 테이블

| 요구사항 | 유닛 | 비고 |
|----------|------|------|
| **FR-01** 인증 시스템 완성 | 유닛 2 (인증) | Cognito JWKS + 카카오/구글 |
| **FR-02** Worker 전체 파이프라인 | 유닛 3 (Worker) | DB 직접, E2E 분석 |
| **FR-03** 음성 전사 (STT) | 유닛 3 (Worker) | Transcribe handler 구현 |
| **FR-04** PDF Evidence Pack | 유닛 4 (PDF) | WeasyPrint + 폰트 |
| **FR-05** 커뮤니티 배포 | 유닛 5 (Frontend) | Next.js 커뮤니티 화면 |
| **FR-06** 카카오톡 봇 | 유닛 1 (인프라) | HTTPS 필요, 기존 코드 동작 |
| **FR-07** Next.js 프론트엔드 | 유닛 5 (Frontend) | 전체 화면 구현 |
| **NFR-01** HTTPS/TLS | 유닛 1 (인프라) | ACM + ALB |
| **NFR-02** 보안 Baseline | 유닛 1 (인프라) + 유닛 2 (인증) | 미들웨어 + 인증 |
| **NFR-03** 복원력 | 유닛 1 (인프라) + 유닛 3 (Worker) | Health check, DLQ, graceful degradation |
| **NFR-04** PBT | 유닛 6 (PBT) | Hypothesis 규칙엔진 테스트 |
| **NFR-05** 성능 | 유닛 3 (Worker) | 분석 5분 이내 |
| **NFR-06** 비용 | 유닛 1 (인프라) | 최소 사양 유지 |
| **NFR-07** 가용성 | 유닛 1 (인프라) | ECS health check 자동 복구 |
| **NFR-08** 관측성 | 유닛 1 (인프라) | ALB 로깅, CloudWatch (이미 구축) |

## 유닛별 요구사항 커버리지

| 유닛 | 담당 요구사항 | 개수 |
|------|-------------|------|
| 유닛 1 (인프라/보안) | FR-06, NFR-01, NFR-02(일부), NFR-03(일부), NFR-06, NFR-07, NFR-08 | 7 |
| 유닛 2 (인증) | FR-01, NFR-02(일부) | 2 |
| 유닛 3 (Worker) | FR-02, FR-03, NFR-03(일부), NFR-05 | 4 |
| 유닛 4 (PDF) | FR-04 | 1 |
| 유닛 5 (Frontend) | FR-05, FR-07 | 2 |
| 유닛 6 (PBT) | NFR-04 | 1 |

## 미할당 요구사항

없음 — 모든 요구사항이 유닛에 매핑됨.
