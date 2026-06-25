# BADA 팀 역할 배분 (6/25 갱신)

## 현재 진행 상태

| 구분 | 상태 |
|------|------|
| AWS 인프라 (ECS, ALB, RDS, S3, SQS, Route53) | ✅ 배포 완료 |
| Backend API (FastAPI, 보안, 인증) | ✅ 배포 완료 |
| Worker 분석 파이프라인 (SQS 연동 완료) | ✅ 배포 완료 |
| HTTPS + 도메인 (badasoft.com) | ✅ 적용 완료 |
| Frontend (Next.js) | 🔄 PR 대기 중 |
| 모바일 앱 (React Native + Expo) | ✅ M1~M3 완료, 딥링크 대기 |
| 모니터링 (Prometheus + Grafana + Alert) | ✅ 코드 완료, terraform apply 대기 |
| GPS 사건 종속 + 포그라운드 | ✅ 완료 |
| 챗봇 case_id UUID + report.pdf | ✅ 완료 |
| Cognito 모바일 딥링크 | ❌ 미구현 |

---

## MVP 잔여 작업 (~6/27)

### P0: 서비스 E2E 완성

| 작업 | 담당 | 상태 |
|------|------|------|
| Cognito 모바일 딥링크 (`bada://auth`) | 백엔드 | ❌ |
| Frontend PR merge + E2E | 프론트 | ⏳ |
| Worker E2E 검증 (분석→SQS→PDF 생성) | 모니터링/백엔드 | ⏳ (코드 연결 완료) |
| Grafana terraform apply + 검증 | 인프라 | ⏳ |
| 모바일 E2E (로그인→사건→증거→분석) | 모바일 | ⏳ (딥링크 의존) |

### P1: 기능 검증

| 작업 | 담당 |
|------|------|
| Bedrock 실호출 OCR/분석 검증 | Agent/OCR |
| GPS 백그라운드 (개발빌드) | 모바일 |
| 음성 전사 (STT) E2E | 모니터링 |
| AI 챗봇 RAG 실호출 | Agent |

---

## 프로덕션 리팩터링 로드맵 (6/28~)

> MVP 기능 완료 후, 실 서비스 품질을 위해 순차 적용.

### Phase A: 인프라 구조 개선 (6/28~29)

| 작업 | 상세 | 문서 |
|------|------|------|
| Terraform 서비스별 분리 | 단일 state → 9개 서비스별 state | `docs/infra-terraform-refactoring.md` |
| CI/CD paths 정비 | 서비스별 정확한 배포 트리거 | - |

### Phase B: 고가용성 적용 (6/29~30)

| 작업 | 상세 | 문서 |
|------|------|------|
| Backend ECS desired=2 + Auto Scaling | CPU 70% 기반 scale out | `docs/high-availability-design.md` |
| RDS Multi-AZ | `multi_az = true` | `docs/high-availability-design.md` |
| Worker Auto Scaling | SQS 메시지 수 기반 | `docs/high-availability-design.md` |

### Phase C: 운영 안정화 (6/30~7/1)

| 작업 | 상세 |
|------|------|
| Grafana Alert 검증 + 복구 테스트 | `docs/monitoring-alert-test-scenario.md` |
| 백업/복원 검증 | RDS 스냅샷 복원 테스트 |
| 부하 테스트 | 동시 요청 시 Auto Scaling 동작 확인 |
| 보안 점검 | WAF, 인증 토큰 만료, Rate Limit |

### Phase D: 발표 준비 (7/1~)

| 작업 | 상세 |
|------|------|
| 데모 시나리오 + 시드 데이터 | E2E 시연 준비 |
| 아키텍처 다이어그램 갱신 | 최종 구조 반영 |
| 발표 자료 | 설계 결정, 트레이드오프, 결과 |

---

## 참고 문서

| 문서 | 위치 |
|------|------|
| 인프라 검증 현황 | `docs/infra-verification-0625.md` |
| 고가용성 설계 | `docs/high-availability-design.md` |
| Terraform 분리 설계 | `docs/infra-terraform-refactoring.md` |
| 모니터링 설계 + 구현현황 | `aidlc-docs/construction/monitoring/monitoring-design.md` |
| Alert 테스트 시나리오 | `docs/monitoring-alert-test-scenario.md` |
| 모바일 앱 설계 | `aidlc-docs/construction/mobile/mobile-setup.md` |
| API 문서 | `aidlc-docs/inception/reverse-engineering/api-documentation.md` |
