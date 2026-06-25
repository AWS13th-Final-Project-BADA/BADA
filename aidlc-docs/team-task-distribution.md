# BADA 팀 태스크 배분 (6/25 갱신)

> 의사결정 20건 확정 후 재배분. 상세: `docs/decision-record-20260625.md`

---

## 원칙

- Terraform 코드(.tf) 수정: **전원 가능** → PR로 제출
- Terraform apply: **인프라 담당(E)만** 실행
- Phase 2는 5번(TF 분리)이 선행 조건

---

## 역할별 배분

### A. 모바일 담당

| # | 작업 | 시간 | 산출물 |
|---|------|------|--------|
| 19 | 모바일 로그인 E2E (Cognito OAuth → 토큰 수신 → API 호출) | 2~3h | 스크린샷/영상 |
| 20 | APK 배포 파이프라인 (EAS Build + GH Action workflow) | 반나절 | `.github/workflows/build-mobile.yml` + Preview APK |
| — | Phase 4: 모바일 E2E 시나리오 (로그인→사건→증거→분석→PDF) | 반나절 | 테스트 결과 문서 |

### B. 백엔드 담당

| # | 작업 | 시간 | 산출물 |
|---|------|------|--------|
| 3 | 행 수준 인가 (cases + evidences + analysis + report) | 2~3h | `deps.py` + router 수정 |
| 14 | 구조화 로깅 (python-json-logger + request_id) | 2~3h | 미들웨어 + requirements 추가 |
| 10 | X-Ray SDK 통합 (Backend + Worker) | 반나절 | 미들웨어 + requirements + ECS 환경변수 |
| 13 | Task Role 분리 .tf 작성 (Backend/Worker IAM 분리) | 2h | PR → E가 apply |

### C. Agent/OCR 담당

| # | 작업 | 시간 | 산출물 |
|---|------|------|--------|
| 6 | Bedrock 모델 비교 (Opus/Sonnet/Haiku × 10케이스) | 반나절 | 벤치마크 리포트 (`docs/model-benchmark.md`) |
| 7 | WAF .tf 작성 (Web ACL + OWASP Rule + ALB 연결) | 2~3h | PR → E가 apply |
| 11 | GuardDuty + Security Hub .tf 작성 | 1~2h | PR → E가 apply |

### D. 모니터링 담당

| # | 작업 | 시간 | 산출물 |
|---|------|------|--------|
| 17 | CI 강화 (pytest-cov + bandit + ruff + ci.yml) | 2~3h | ci.yml 수정 + 설정 파일 |
| 4 | Auto Scaling .tf 작성 (Backend CPU + Worker SQS + ignore_changes) | 2~3h | PR → E가 apply |
| 15 | Fargate Spot .tf 작성 (Worker capacity provider) | 1h | PR → E가 apply |
| 9 | k6 부하 테스트 (스크립트 + 실행 + 그래프 캡처) | 반나절 | k6 스크립트 + Grafana 스크린샷 |

### E. 인프라 담당

| # | 작업 | 시간 | 산출물 |
|---|------|------|--------|
| 16 | Terraform Plan in PR (GH Action workflow) | 1~2h | `.github/workflows/terraform-plan.yml` |
| 5 | TF 분리 실행 (network/data/compute + state mv) | 반나절 | 분리된 디렉토리 구조 |
| 2/8 | RDS 재생성 (암호화 + Multi-AZ) | 2h | apply 완료 |
| 12/18 | Private Subnet + NAT GW + VPC Endpoint | 반나절 | apply 완료 |
| — | B, C, D의 .tf PR 리뷰 + plan 확인 + apply | 상시 | — |
| — | `frontend_enabled = false` apply (웹 프론트 제거) | 10min | — |

---

## 실행 일정

### Day 1 (6/25~26): Phase 1 — 전원 병렬

```
A: 19(모바일 로그인) → 20(APK 파이프라인)
B: 3(행 수준 인가) → 14(구조화 로깅) → 10(X-Ray SDK)
C: 6(Bedrock 모델 비교)
D: 17(CI 강화)
E: 16(TF Plan PR) + frontend_enabled=false apply
```

### Day 2~3 (6/27~28): Phase 2 — TF 분리 + 인프라 추가

```
E: 5(TF 분리) → 2/8(RDS 암호화+Multi-AZ) → 12/18(Private Subnet+NAT+VPC Endpoint)
B: 13(Task Role .tf) → PR 제출
C: 7(WAF .tf) + 11(GuardDuty .tf) → PR 제출
D: 4(Auto Scaling .tf) + 15(Spot .tf) → PR 제출
E: 위 PR 리뷰 → plan → apply
A: (여유 시 모바일 UI 개선 또는 다른 팀 지원)
```

### Day 4 (6/29~30): Phase 4 — 검증 + 캡처

```
D: 9(k6 부하 테스트 → Auto Scaling 발동 → Grafana 그래프 캡처)
A: 모바일 E2E (로그인→사건→증거→분석→PDF)
전원: 최종 검증 + 발표 자료용 스크린샷 수집
```

---

## 의존성 다이어그램

```
Phase 1 (병렬)
├── A: 19 → 20
├── B: 3 → 14 → 10
├── C: 6
├── D: 17
└── E: 16

Phase 2 (E의 TF 분리 완료 후)
├── E: 5 → 2/8 → 12/18
├── B: 13 ─┐
├── C: 7, 11 ─┤── E가 일괄 apply
└── D: 4, 15 ─┘

Phase 4 (Phase 3 apply 완료 후)
├── D: 9 (부하 테스트)
└── A: 모바일 E2E
```

---

## 차단 요소 (Blockers)

| 항목 | 의존 대상 | 해결 시점 |
|------|----------|----------|
| 모바일 로그인 (#19) | Cognito callback + Expo 개발빌드 | Day 1 |
| APK 배포 (#20) | EAS 계정 + expo login 토큰 | Day 1 |
| .tf PR apply | E의 TF 분리 완료 (#5) | Day 2 |
| k6 테스트 (#9) | Auto Scaling apply 완료 (#4) | Day 4 |
| 모바일 E2E | 모바일 로그인 + Worker E2E 정상 | Day 4 |

---

## 참고 문서

| 문서 | 위치 |
|------|------|
| 의사결정 전체 | `docs/decision-record-20260625.md` |
| 인프라 현황 | `docs/infra-implementation-status.md` |
| TF 분리 설계 | `docs/infra-terraform-refactoring.md` |
| 모바일 설계 | `aidlc-docs/construction/mobile/mobile-setup.md` |
| 모니터링 설계 | `aidlc-docs/construction/monitoring/monitoring-design.md` |
