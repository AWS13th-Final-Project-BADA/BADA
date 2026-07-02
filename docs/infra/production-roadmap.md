# 프로덕션 전환 로드맵

> MVP 완성 후, 실 서비스 품질을 갖추기 위해 단계적으로 적용할 항목.
> 각 Phase는 독립적으로 적용 가능하며, 비즈니스 우선순위에 따라 순서 조정 가능.

---

## Phase 1: 보안 강화 (최우선)

BADA는 이주노동자의 임금/근로 증거를 다루는 서비스로, 민감 개인정보 보호가 법적 의무.

### 네트워크 보안

| 항목 | 현재 | 목표 | 작업 |
|------|------|------|------|
| ECS 배치 | Public Subnet | Private Subnet + NAT GW | 보류 (종료 기간·비용 대비 위험 초과 — To-Be 다이어그램으로 갈음) |
| WAF | **적용 완료** (AWS WAF v2 — IP평판 + OWASP Common + KnownBadInputs 3종 관리형 룰셋, ALB 연결) | 유지 | - |
| 위협 탐지 | 없음 | GuardDuty + Security Hub | **적용 완료** (GuardDuty S3 logs 탐지, Security Hub FSBP, HIGH severity→SNS, `security_monitoring_enabled` 종료 토글, PR #207) |
| Security Group | 최소 포트 허용 | 동일 (유지) | - |

### 인증/인가 강화

| 항목 | 현재 | 목표 | 작업 |
|------|------|------|------|
| JWT 토큰 만료 | 설정 확인 필요 | Access 15분 / Refresh 7일 | Cognito 설정 |
| 행 수준 인가 | **적용 완료** (Cases/Evidences 소유자 검증) | 유지 | - |
| Secrets 로테이션 | 수동 | 자동 (90일) | Secrets Manager rotation Lambda |
| Task Role 분리 | **적용 완료** (Backend/Worker 서비스별 최소권한 Role — Backend=producer/SQS Send, Worker=consumer/SQS Receive, PR #205) | 유지 | - |

### 개인정보 보호 (법적 필수)

| 항목 | 현재 | 목표 | 근거 |
|------|------|------|------|
| 위치정보 수집 동의 | 없음 | 별도 동의 화면 | 위치정보법 제18조 |
| 개인정보처리방침 | 없음 | 앱/웹 동의 화면 | 개인정보보호법 |
| 회원 탈퇴 + 데이터 삭제 | 없음 | RDS + S3 원본 완전 삭제 | 개인정보보호법 제36조, GDPR Art.17 |
| 데이터 보관 기간 | 무기한 | 사건 종료 후 3년 보관 → 자동 삭제 | 근로기준법 시효 3년 |
| 접근 로그 | CloudWatch만 | CloudTrail + 개인정보 접근 이력 | 개인정보보호법 제29조 |

---

## Phase 2: 고가용성 + 성능

> 상세 설계: `docs/infra/high-availability-design.md`

### 가용성

| 항목 | 작업 | 효과 | 현황 (7/1) |
|------|------|------|------|
| Backend Auto Scaling | CPU 70% Target Tracking (min=1/max=3) | 부하 대응·단일 장애점 완화 | **적용 완료** (PR #203) |
| RDS Multi-AZ | `multi_az = true` | 자동 failover (30~60초) | **적용 완료** |
| Worker Auto Scaling | SQS backlog-per-task Target Tracking (min=1/max=3) | 분석 급증 대응 | **적용 완료** (PR #203) |
| Worker CPU 상향 | 256→1024 (1 vCPU), Memory 512→2048 | PDF 생성 50초→15초 | **적용 완료** |
| OCR 병렬 처리 | ThreadPoolExecutor(max_workers=50) | 12건 240초→25초 | **적용 완료** |
| 1-pass OCR | Bedrock 호출 2→1회 | 증거당 ~20초 절약 | **적용 완료** |

### 성능

| 항목 | 작업 | 효과 |
|------|------|------|
| CloudFront CDN | Frontend 정적 자산 캐싱 | 글로벌 응답 속도 개선 |
| RDS Proxy | Connection Pooling | 커넥션 고갈 방지 (현재 max ~100) |
| ElastiCache Redis | 세션/분석 결과 캐싱 | DB 부하 감소 |
| S3 Lifecycle | 90일 → IA, 1년 → Glacier | 스토리지 비용 60% 절감 — **Evidence/Report 적용 완료** (2026-07-02, `s3_lifecycle_enabled` 토글, IA 90d→Glacier 365d + MPU 정리). ALB 로그는 30일 만료 별도 적용 |

---

## Phase 3: 운영 성숙도

### 관측성 (Observability)

| 항목 | 현재 | 목표 |
|------|------|------|
| Logging | CloudWatch (비구조화) | 구조화 JSON 로깅 + 중앙 집계 |
| Metrics | Prometheus + CloudWatch | 유지 (충분) |
| Tracing | 없음 | AWS X-Ray 또는 OpenTelemetry — API→SQS→Worker 추적 |

### 배포 전략

| 항목 | 현재 | 목표 |
|------|------|------|
| 배포 방식 | Rolling Update | Blue/Green (ECS CodeDeploy) |
| 롤백 | Circuit Breaker (자동) | 즉시 롤백 + 트래픽 전환 |
| Feature Flag | 없음 | LaunchDarkly 또는 AppConfig |
| Canary 배포 | 없음 | 5% 트래픽 → 검증 후 100% |

### 인시던트 관리

| 항목 | 현재 | 목표 |
|------|------|------|
| On-Call | 없음 | PagerDuty 또는 SNS escalation |
| Runbook | `docs/runbooks/` 일부 | 모든 Alert Rule에 대응 Runbook 매핑 |
| 포스트모템 | 없음 | 장애 후 문서화 + 재발 방지 |

---

## Phase 4: 비용 최적화

| 항목 | 작업 | 절감 효과 |
|------|------|----------|
| Worker Fargate Spot | Worker capacity provider `FARGATE_SPOT` 전환 (SQS+DLQ 멱등성으로 중단 안전, Backend는 On-Demand 유지) | **적용 완료** (PR #206) — Worker 컴퓨트 비용 절감 |
| Fargate Savings Plan | 1년 약정 | 30~50% |
| S3 Intelligent-Tiering | 자동 계층 이동 | 스토리지 비용 자동 최적화 |
| Bedrock 사용량 제한 | 사용자당 일일 분석 N회 | 비용 폭주 방지 |
| AWS Budgets | 월 예산 알림 | 초과 시 즉시 인지 |
| 개발 환경 스케줄링 | 야간/주말 desired=0 | 개발 인프라 70% 절감 |

---

## Phase 5: 재해 복구 (DR)

> DR 수준(Backup&Restore / Pilot Light / Warm Standby)과 확정 RTO/RPO, 복원 리허설
> 절차는 **단일 출처** `docs/operations/rto-rpo-and-restore-rehearsal.md`를 참조한다.

MVP 직후: Backup & Restore (현재 RDS 자동 백업 7일 이미 활성화)
운영 안정화 후: Pilot Light 검토

---

## 적용 기준

| 트리거 | Phase |
|--------|-------|
| MVP 완성 즉시 | Phase 1 (보안 — 법적 필수) |
| 실 사용자 유입 | Phase 2 (HA + 성능) |
| 운영 1개월 | Phase 3 (운영 성숙도) |
| 월 비용 $200+ | Phase 4 (비용 최적화) |
| SLA 계약 체결 | Phase 5 (DR) |

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| `docs/infra/high-availability-design.md` | HA 상세 설계 + Terraform 코드 |
| `docs/infra/terraform-refactoring.md` | Terraform 서비스별 분리 설계 |
| `docs/infra/security-operations-plan.md` | ECR 스캔, Task Role 분리 |
| `docs/decisions/privacy-legal-requirements.md` | 법무 요건 (동의/삭제/보관) |
| `aidlc-docs/team-task-distribution.md` | 팀 배분 + 일정 |
