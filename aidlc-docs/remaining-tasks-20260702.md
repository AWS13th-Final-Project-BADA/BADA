# BADA 남은 태스크 정리 (2026-07-02)

> AIDLC 기반 전체 분석 결과, 프로덕션 전환을 위해 남은 태스크를 정리한 문서.
> 근거: `aidlc-state.md`, `docs/infra/implementation-status.md`, `docs/infra/production-roadmap.md`,
> `docs/decisions/decision-record-20260625.md`, `docs/decisions/privacy-legal-requirements.md`,
> 그리고 실제 `infra/*.tf` 코드 교차 검증.

## 0. 현재 성숙도 요약

- AIDLC 전 단계 완료: Inception(역공학→요구사항→설계→유닛) → Construction(6유닛+빌드/테스트) → Post-MVP 고도화
- 확정 의사결정 20건 중 **17건 완료 / 3건 의도적 보류(#5·#12·#18)**
- Well-Architected Tool 1차 리뷰(57문항) 등록, High 30 / Medium 24 (대부분 dev 환경 의도적 미뤄둠)
- **핵심 발견**: 유일한 애플리케이션 계층 공백은 "법적 필수(개인정보) 기능"이며, 인프라는 이미 dev/포트폴리오 수준을 초과함

## 제약 조건 (모든 태스크 판단의 전제)

| 제약 | 값 |
|---|---|
| 프로젝트 유지 종료 | 2026-07-10 (약 1주 남음) |
| 예산 상한 / 사용 | $1,500 / ~$55 |
| 목적 | 데모·포트폴리오 (실서비스 트래픽 거의 없음) |
| reversible 필수 | 켠 리소스는 종료 절차 확보 필수 |
| 변경 방식 | Terraform 코드 → PR → plan → apply (콘솔 직접수정 금지) |

---

## 카테고리 A — 법적 필수 (애플리케이션 계층 공백)

> 임금·GPS 등 민감정보 처리 서비스의 법적 의무. 인프라가 아닌 **백엔드/앱 코드 공백**.
> Terraform·백엔드 확인 결과 삭제/동의 엔드포인트 부재.
> 실서비스 전환 시 최우선. 데모/포트폴리오 목적상 종료 전 실装 여부는 선택.

| ID | 태스크 | 법적 근거 | 구현 범위 | 상태 |
|---|---|---|---|---|
| A-1 | 회원 탈퇴 + 데이터 완전 삭제 | 개인정보보호법 §36, GDPR Art.17 | RDS 레코드 삭제 + S3 원본 `s3:DeleteObject` 연동 엔드포인트 | 미구현 |
| A-2 | 개인정보 수집·이용 동의 화면 + 처리방침 | 개인정보보호법 §15, §26/§28의8 | 수집항목·목적·보유기간 명시, 수탁자(AWS/Anthropic) + **국외이전 동의** | 미구현 |
| A-3 | 위치정보 별도 동의 + 확인자료 보관 | 위치정보법 §18 | 위치권한 목적 고지, 수집이용 확인자료 6개월 보관 | 부분(핑 로그 존재, 동의/보관정책 미비) |
| A-4 | 데이터 보관기간 자동 파기 | 근로기준법 시효 3년 | 사건 종료 후 3년 → 자동 삭제 배치 | 미구현 |

## 카테고리 B — Well-Architected 잔여 리스크 (대기)

> WA 1차 리뷰의 P1/P2 대기 항목. 저비용·reversible 위주로 종료 전 처리 가능한 것 다수.

| ID | 태스크 | Pillar | 우선순위 | 상태 |
|---|---|---|---|---|
| B-1 | RTO/RPO 정의 + RDS restore rehearsal 절차 | Reliability | P1 | 대기 |
| B-2 | Dependency scan(SCA) CI 추가 (pip-audit/Trivy/Dependabot) | Security | P1 | **구현 완료 (2026-07-02)** — `.github/workflows/ci.yml`에 pip-audit 잡 추가(backend/worker requirements). 초기 non-blocking(continue-on-error), 리포트 축적 후 하드 게이트 전환 예정 |
| B-3 | ECR 이미지 Critical/High 취약점 해소 | Security | P1 | 부분 (Backend Critical 1/High 3 등) |
| B-4 | Cost allocation tag + Cost Explorer/CUR 분석 | Cost | P2 | 대기 |
| B-5 | S3 Evidence/Report Lifecycle·retention 정책 | Security/Sustainability | P2 | **구현 완료 (2026-07-02)** — `infra/data.tf` lifecycle(IA 90d→Glacier 365d + MPU 정리), `s3_lifecycle_enabled` 종료 토글. fmt/validate 통과. plan/apply는 PR에서 담당자 |

## 카테고리 C — 의도적 보류 (판단 타당, 유지)

> 종료 일정·비용 대비 위험이 가치를 초과. To-Be 다이어그램으로 갈음.

| ID | 태스크 | 보류 사유 | 개략 비용(2주) |
|---|---|---|---|
| C-1 (#5) | Terraform 3분할 (network/data/compute) | state mv 위험, 종료 임박 | $0 |
| C-2 (#12) | ECS → Private Subnet + NAT Gateway | NAT 고정비 + reversible 비용 | ~$65 |
| C-3 (#18) | VPC Endpoint (Interface: SQS/ECR) | #12와 세트, 단독 실익 낮음 | ~$7 |

---

## 실행 계층 (남은 1주 기준 권장 순서)

### 계층 1 — 지금 하면 가치 큼 (저비용·reversible·코드 위주)

| 순번 | 태스크 | 매핑 | 비용/리스크 | 되돌리기 |
|---|---|---|---|---|
| 1 | S3 Evidence/Report Lifecycle (90d→IA, 1y→Glacier, incomplete MPU 정리) | B-5 | ~$0 | 쉬움(설정 제거) |
| 2 | Dependency scan CI 워크플로 추가 | B-2 | $0 | 쉬움 |
| 3 | VPC Endpoint **S3 Gateway만**(무료) | C-3 일부 | 무료 | 쉬움 |
| 4 | RDS restore rehearsal 1회 + RTO/RPO 문서화 | B-1 | 스냅샷 소액 | 스냅샷 삭제 |
| 5 | Cost allocation tag + Cost Explorer 캡처 | B-4 | $0 | 쉬움 |

### 계층 2 — 데모 임팩트용, 토글 (선택적, 대체로 보류 권장)

| 태스크 | 판단 |
|---|---|
| CloudFront (정적 캐싱) | 웹 프론트 제거로 실익 제한 → 보류 |
| Blue/Green (ECS CodeDeploy) | circuit breaker 자동 롤백으로 충분 → 보류 |
| Secrets 자동 로테이션(90d) | rotation Lambda 필요, dev 실익 낮음 → 보류 |

### 계층 3 — 실사용자 유입 후 (현재 명시적 제외)

| 태스크 | 제외 사유 |
|---|---|
| ElastiCache Redis | idle 비용만 발생, 트래픽 없음 → 낭비 |
| RDS Proxy | 커넥션 고갈 이슈 없음 |
| Fargate Savings Plan(1년) | 종료 예정이라 약정 위험 |
| Private Subnet + NAT (#12) | ~$65 + reversible 비용, To-Be 다이어그램 갈음 |

---

## 최우선 단일 선택

**S3 Evidence/Report Lifecycle (B-5) + RDS restore rehearsal·RTO/RPO 문서화 (B-1)**

- 둘 다 거의 무료 + reversible
- "민감 데이터 라이프사이클 관리 + 검증된 복구 절차"는 임금체불 증거 서비스의 프로덕션 준비성을 가장 설득력 있게 증명
- 포트폴리오/데모에서 Reliability·Security·Sustainability 3개 Pillar를 동시에 커버

---

## 종료(7/10) 정리 체크리스트 연동

신규로 켠 리소스가 있으면 아래에 추가로 반영 (기존 체크리스트: `docs/runbooks/project-closure.md`):
- S3 Lifecycle: 설정 제거만 하면 됨 (데이터 삭제와 별개)
- VPC S3 Gateway Endpoint: 무료지만 종료 시 destroy 대상
- RDS rehearsal 스냅샷: 검증 후 삭제
- 기존 토글: `backend/worker_autoscaling_enabled`, `security_monitoring_enabled`, `worker_fargate_spot_enabled` = false 복귀

---

## 가드레일

- 모든 인프라 변경: Terraform 코드 → PR → `terraform plan` → 담당자 apply (콘솔 직접수정 금지)
- Auto Scaling과 `desired_count` 충돌 방지: `ignore_changes=[desired_count]` 유지 (이미 적용)
- 부하 테스트는 팀 데모 시간대 회피
- 켠 리소스는 반드시 종료 절차 문서화
