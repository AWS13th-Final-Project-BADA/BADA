# BADA 의사결정 기록 (2026-06-25)

> AI-DLC 분석 기반, 팀 리드 승인 완료.
> MVP 잔여 작업 + 프로덕션 고도화 전체 범위.

---

## 배경

- 프로젝트 종료: 2026-07-10
- 예산 잔여: ~$1,445 / $1,500
- 목적: 포트폴리오 가치 극대화 + Well-Architected 리스크 해소 + 데모 임팩트

---

## 추가 결정 (웹 프론트엔드 → 모바일 전환)

| # | 항목 | 결정 |
|---|------|------|
| — | 웹 프론트엔드 (Next.js) | 제거. `frontend_enabled=false` → ALB default → Backend static 서빙 |
| — | deploy-dev-frontend.yml | 삭제 완료 (`bb58341`) |
| — | badasoft.com | Backend static/index.html로 폴백 (앱 다운로드 안내 전환 가능) |
| — | 주력 프론트엔드 | `mobile-native/` (React Native + Expo) |

---

## 확정 의사결정 (18건)

> **실행 상태 (2026-07-02 갱신)**
> - ✅ **완료**: 1(소셜 OAuth 직접구현)·2(RDS 암호화)·3(행수준 인가)·4(Auto Scaling, PR #203)·6(모델 비교)·7(WAF)·8(Multi-AZ)·9(k6 부하 검증 — Backend 1→2, Worker 1→3, PR #212/#213)·10(X-Ray)·11(GuardDuty/Security Hub + 종료 토글, PR #207)·13(Task Role 분리, PR #205)·14(구조화 로깅)·15(Worker Fargate Spot, PR #206)·16(TF Plan-in-PR)·17(CI 강화)·19(모바일 로그인 E2E — 코드 완비)·20(APK 파이프라인)
> - 🔧 **보류**: 5(TF 분리)·12(ECS Private Subnet+NAT) — 종료 기간(7/10)·비용 대비 위험이 가치를 초과. To-Be 다이어그램으로 갈음. 18(VPC Endpoint)은 **S3 Gateway(무료) 부분 완료(2026-07-02)**, Interface Endpoint(SQS/ECR, ~$7)는 보류.
> - ✅ **추가 완료 (2026-07-02, 로드맵/WA 항목)**: S3 Evidence/Report Lifecycle(B-5), Dependency scan CI(B-2), S3 Gateway VPC Endpoint(C-3 일부), RTO/RPO 정의+복원 리허설 문서(B-1), 비용 할당 태그 default_tags(B-4), 의존성 취약점 저위험 범프(B-3 부분). 상세: `aidlc-docs/remaining-tasks-20260702.md`
> - 🚧 **담당 진행**: (없음 — 20건 전부 완료 또는 보류로 종결)
> - 참고(모바일): #20 APK 빌드는 EAS 무료 쿼터(월 15회) 절약을 위해 **수동 실행(`workflow_dispatch`) 전용**으로 전환(자동 push 빌드 제거). #1은 앱 계층 소셜 OAuth로 단일화 완료이며 **Cognito 미사용 협의**(리소스는 잔존, 종료 시 정리).
> - 참고: 4·11·13·15는 원래 "TF 분리(5) 후" 조건이었으나, TF 분리 없이 단일 `infra/`에서 안전하게 적용함(#4는 `ignore_changes=[desired_count]`, #11은 `moved` 블록, #15는 `capacity_provider_strategy`).
> - 상세 현황: `docs/infra/implementation-status.md`

| # | 항목 | 결정 | 비용(2주) | 실행 조건 |
|---|------|------|-----------|----------|
| 1 | 모바일 인증 | Cognito 제거 → 소셜 OAuth 직접 구현 (Google + Kakao + Naver) | $0 | 진행 |
| 2 | RDS 암호화 | Phase A Terraform 분리 시 `storage_encrypted=true`로 신규 생성 | $0 | TF 분리 후 |
| 3 | 행 수준 인가 | Cases + Evidences API에 `case.user_id == 요청자` 검증 | $0 | 즉시 |
| 4 | Auto Scaling | Backend CPU 70% + Worker SQS backlog 기반 (min=1/max=3) | ~$5 | TF 분리 후 |
| 5 | Terraform 분리 | 3분할 (network/data/compute), E2E 완료 후 조건부 | $0 | P0 E2E 후 |
| 6 | Bedrock 모델 비교 | Opus 4 / Sonnet 4 / Haiku 3.5 × 10케이스 벤치마크 | ~$15 | 즉시 |
| 7 | WAF | ALB 앞단 AWS WAF (OWASP Managed Rule Set) | ~$15 | TF 분리 후 |
| 8 | RDS Multi-AZ | Phase A 재생성 시 `multi_az=true` | ~$20 | TF 분리 후 |
| 9 | k6 부하 테스트 | Auto Scaling 발동 증명 + Grafana/CloudWatch 그래프 캡처 | ~$5 | AS 적용 후 |
| 10 | X-Ray 분산 추적 | Backend + Worker SDK 통합 (Service Map 시각화) | ~$5 | 즉시 |
| 11 | GuardDuty / Security Hub | Terraform으로 활성화 | ~$12 | TF 분리 후 |
| 12 | ECS → Private Subnet | NAT Gateway 추가, ECS를 Private Subnet으로 이동 | ~$65 | TF 분리 후 |
| 13 | Task Role 분리 | Backend/Worker 각각 최소권한 IAM Role | $0 | TF 분리 후 |
| 14 | 구조화 로깅 | JSON 로그 + request_id correlation | $0 | 즉시 |
| 15 | Fargate Spot (Worker) | Spot capacity provider 전환 (SQS+DLQ 멱등성으로 안전) | -$3 | TF 분리 후 |
| 16 | Terraform Plan in PR | GitHub Action으로 PR에 plan 결과 자동 코멘트 | $0 | 즉시 |
| 17 | CI 강화 | pytest-cov + bandit (SAST) + ruff (lint) | $0 | 즉시 |
| 18 | VPC Endpoint | S3 Gateway (무료) + SQS/ECR Interface Endpoint | ~$7 | **S3 Gateway 완료(2026-07-02)**, Interface는 12번과 세트로 보류 |

| 19 | 모바일 로그인 E2E | 소셜 OAuth(구글/카카오/네이버) → 토큰 수신 검증 | $0 | 즉시 |
| 20 | APK 배포 파이프라인 | EAS Build + GH Action + Preview APK | $0 | 즉시 |

**총 예상 추가 비용: ~$144/2주** (예산의 10%)

---

## 실행 로드맵

### Phase 1: 즉시 가능 (코드 변경, 인프라 불변)

| # | 작업 | 예상 시간 | 담당 |
|---|------|----------|------|
| 19 | 모바일 로그인 E2E (소셜 OAuth 구글/카카오/네이버 → 토큰 수신) | 2~3h | 모바일 + Backend |
| 20 | APK 배포 파이프라인 (EAS Build + GH Action) | 반나절 | 모바일 + 인프라 |
| 3 | 행 수준 인가 (deps.py + routers) | 2~3h | Backend |
| 6 | Bedrock 모델 비교 (eval 스크립트) | 반나절 | Agent/OCR |
| 10 | X-Ray SDK 통합 + Task Role 권한 추가 | 반나절 | Backend + 인프라 |
| 14 | 구조화 로깅 (python-json-logger) | 2~3h | Backend |
| 16 | Terraform Plan in PR (GH Action) | 1~2h | 인프라 |
| 17 | CI 강화 (coverage/bandit/ruff) | 2~3h | 인프라/Backend |

### Phase 2: Terraform 분리 (6/28~ 조건부)

| 단계 | 작업 |
|------|------|
| 2-1 | `infra/` → `infra/network/`, `infra/data/`, `infra/compute/` 분할 |
| 2-2 | `terraform state mv` + remote state data source 연결 |
| 2-3 | RDS 재생성 (`storage_encrypted=true`, `multi_az=true`) |
| 2-4 | ECS → Private Subnet + NAT GW + VPC Endpoint |
| 2-5 | Task Role 분리 (Backend: S3 PUT + SQS Send / Worker: S3 + SQS Receive + Bedrock + Transcribe) |

### Phase 3: 인프라 추가 기능 (Phase 2 완료 후)

| # | 작업 |
|---|------|
| 4 | Auto Scaling policy (CPU + SQS) + `ignore_changes=[desired_count]` |
| 7 | WAF Web ACL + ALB 연결 |
| 11 | GuardDuty + Security Hub 활성화 |
| 15 | Worker capacity provider → Fargate Spot |

### Phase 4: 최종 검증 (6/30~)

| # | 작업 |
|---|------|
| 9 | k6 부하 테스트 → Auto Scaling 발동 + X-Ray Service Map + Grafana 그래프 캡처 |
| — | E2E 전체 흐름 검증 (모바일→Backend→Worker→PDF) |
| — | 발표 자료용 스크린샷 수집 |

---

## 의사결정 근거 요약

### 1번: 소셜 OAuth 직접 구현 (Cognito 제거, 구글/카카오/네이버)
- 결정: Cognito Hosted UI를 제거하고 백엔드 소셜 OAuth(구글/카카오/네이버)로 전환
- 백엔드에 소셜 OAuth(`/auth/{provider}/login`·`/callback`, `auth_service.py`)는 이미 구현됨 → 콜백에 앱 딥링크(`bada://auth#token=`) 분기 추가 + `AUTH_MODE` 전환 필요
- 앱은 `WebBrowser.openAuthSessionAsync`로 `/auth/{provider}/login?redirect_uri=bada://auth` 호출

### 2번: RDS 암호화 — Phase A에서
- 사유: 인플레이스 불가 → 재생성 필요 → TF 분리와 동시에 하면 state 충돌 0
- Well-Architected Security Pillar 충족

### 3번: 행 수준 인가 — Cases + Evidences만
- 사유: 핵심 민감 데이터(급여, GPS) 보호, 나머지는 공개(Community) 또는 종속(GPS→Cases)
- 구현: `deps.py`에 소유자 검증 의존성 추가

### 4번: Auto Scaling — min=1/max=3
- 사유: 상시 2대(비용)보다 탄력적 대응(기술 깊이) = 포트폴리오 임팩트 우위
- k6로 실증 그래프 확보

### 5번: Terraform 분리 — 조건부
- 사유: 2/8/12/13/15번의 전제조건이므로 필요하지만, E2E 안정 확인 후 진행

### 6번: Bedrock 모델 비교
- 사유: "근거 기반 모델 선정" = 엔지니어링 의사결정 능력 증명
- 상위(Opus 4) / 기준(Sonnet 4) / 하위(Haiku 3.5) 비교

### 7~18번: 공통 근거
- budget-upgrade-prompt.md 기준: 포트폴리오 가치 + WA 리스크 해소 + 기술 경험
- "비효율적이더라도 기술 써보고 싶어서 채택" — 면접에서 납득 가능한 논리

---

## 종료 체크리스트 (7/10)

7/10 이후 비용 리소스 정리:

> **2026-07-02 갱신**: 아래 항목 중 상당수는 변수 토글로 정리 가능해졌다.
> - Auto Scaling: `backend_autoscaling_enabled=false` / `worker_autoscaling_enabled=false`
> - GuardDuty/Security Hub: `security_monitoring_enabled=false`
> - Worker Fargate Spot: `worker_fargate_spot_enabled=false` (On-Demand 복귀)
> - NAT Gateway / VPC **Interface** Endpoint: **보류로 생성 안 함** → 정리 대상 아님
> - S3 **Gateway** Endpoint(무료, 2026-07-02 추가): 종료 시 `s3_gateway_endpoint_enabled=false`로 제거
> - S3 Evidence/Report Lifecycle: `s3_lifecycle_enabled=false`로 룰 제거(객체 보존)

- [ ] Auto Scaling policy 삭제, desired=0
- [ ] NAT Gateway 삭제
- [ ] VPC Interface Endpoint 삭제
- [ ] WAF Web ACL 삭제
- [ ] RDS final snapshot → 인스턴스 삭제
- [ ] GuardDuty / Security Hub 비활성화
- [ ] ECS 서비스 desired=0 → 클러스터 삭제
- [ ] S3 버킷 비우기 + 삭제 (민감 데이터)
- [ ] Secrets Manager 시크릿 삭제
- [ ] ECR 이미지 삭제
- [ ] CloudWatch Log Group 삭제
- [ ] Cognito User Pool 삭제 (OAuth 전환으로 미사용 — 잔여 리소스 정리)
- [ ] 소셜 OAuth(구글/카카오/네이버) Client Secret 정리 (Secrets Manager/SSM)

상세: `docs/runbooks/project-closure.md` 참조.

---

## 관련 문서

| 문서 | 위치 |
|------|------|
| 예산 활용 가이드라인 | `C:\AIDLC\budget-upgrade-prompt.md` |
| 프로덕션 로드맵 | `docs/infra/production-roadmap.md` |
| 고가용성 설계 | `docs/infra/high-availability-design.md` |
| Terraform 분리 설계 | `docs/infra/terraform-refactoring.md` |
| 팀 역할 배분 | `aidlc-docs/team-task-distribution.md` |
| 인프라 검증 현황 | `docs/infra/verification-0625.md` |
