# 향후 개선점 종합 (회고용)

> 발표/회고를 위해 프로젝트 전 기간의 "남은 과제·개선 필요 항목"을 종합한 문서다.
> MVP 데모/포트폴리오 목적상 의도적으로 보류한 것과, 실서비스 전환 시 반드시 필요한 것을 구분했다.

## 목차

1. [법적 필수 — 실서비스 전환 전 반드시 필요](#1-법적-필수--실서비스-전환-전-반드시-필요)
2. [에이전트 / OCR](#2-에이전트--ocr)
3. [데이터 모델](#3-데이터-모델)
4. [인프라 — Well-Architected 잔여 리스크](#4-인프라--well-architected-잔여-리스크)
5. [의도적으로 보류한 것](#5-의도적으로-보류한-것)
6. [Phase 2/3 범위 밖 (제품 설계상 제외)](#6-phase-23-범위-밖-제품-설계상-제외)

---

## 1. 법적 필수 — 실서비스 전환 전 반드시 필요

> BADA는 임금체불 증거(이름·임금·계좌·제3자 정보, GPS)를 다루는 서비스라 이 카테고리는
> 데모 단계에선 넘어갈 수 있어도 실서비스 전환 시 최우선 순위다.

| 항목 | 근거 | 현재 상태 |
|---|---|---|
| 회원 탈퇴 + 데이터 완전 삭제 | 개인정보보호법 §36, GDPR Art.17 | **미구현**. `DELETE /cases/{id}`, `DELETE /evidences/{eid}`는 DB 레코드만 삭제하고 S3 원본은 그대로 남음 |
| 개인정보 수집·이용 동의 화면 + 처리방침 | 개인정보보호법 §15, §26/§28의8 | **미구현**. 수집항목·목적·보유기간 명시 동의창, AWS/Anthropic 수탁 고지, 국외이전 동의 필요 |
| 위치정보 별도 동의 + 확인자료 보관 | 위치정보법 §18 | **부분**. 핑 로그 자체는 존재(3년 보관, 법정 요건 6개월 상회)하나 동의 UI·보관정책 고지 미비 |
| 보관기간 자동 파기 배치 | 근로기준법 임금채권 소멸시효 3년 | **미구현**. `retention_days`(일반, 90일)·`gps_retention_days`(GPS, 3년) 값은 설정에만 존재하고, 이를 근거로 실행되는 자동 삭제 배치가 없음 |

**참고**: 마지막 항목(GPS 3년 보존 분리, S3 아카이브 lifecycle)은 PR #226에서 **정책값과 Terraform lifecycle 규칙까지는 선반영**했으나, 실제 export/아카이빙 로직과 삭제 배치는 `architecture.md` 6항에 설계만 기록하고 구현은 보류함(GPS 무결성 검증 로직과 얽혀 회귀 위험이 크고, 데모 규모에서 실익이 낮다고 판단).

**원본**: `aidlc-docs/remaining-tasks-20260702.md` 카테고리 A, `docs/decisions/privacy-legal-requirements.md`

---

## 2. 에이전트 / OCR

### 파일명/경로 키워드 기반 후보 선정의 구조적 한계

Expo managed workflow에서 온디바이스 OCR(ML Kit/TFLite)을 못 써서, 갤러리 스캔 2~3단계가 파일명·경로 문자열 매칭으로 대체돼 있다. 이 때문에:
- 카카오톡 폴더/스크린샷 폴더에 있으면 **내용과 무관하게** 후보로 잡힘(셀카, 기프티콘 등 오탐).
- 반대로 실제 증거 사진이 이 패턴에 안 걸리면(예: 일반 `IMG_1234.jpg`) 후보에서 누락됨.

현재는 "디바이스 필터링은 서버 비용 절감용 사전 감축, 최종 판별은 서버 `classify`(Bedrock)"로 역할을 재조정해 완화했지만, 디바이스 단계의 오탐/누락 자체는 해소되지 않았다.

**개선 방향(선택)**: TFLite 경량 모델 학습·탑재(원래 설계에 있었으나 미착수), 또는 클라이언트 필터를 더 완화해서 서버에 넘기는 비중을 늘리는 방향.

### 온디바이스 OCR/분류 (ML Kit·TFLite) 미연동

`agent-feature-brief.md` 설계상 3단계는 경량 모델(TFLite/CoreML) 분류를 예정했으나, 현재는 파일명·폴더 키워드 스코어 폴백으로만 동작.

### 배포 환경 Bedrock 실호출 CloudWatch 로그 실증 대기

코드·트리거는 준비 완료(`category=auto` + `/extract` fire-and-forget)이나, 배포 환경 CloudWatch Logs에서 `Bedrock 응답` 실제 로그로 최종 확인이 남아있음.

**원본**: `docs/architecture/agent-feature-brief.md` 말미 "남은 TODO"

### PDF 경량 폰트 전환 / Haiku 모델 구조화 시도

- PDF 생성 시 한글 폰트(Noto CJK, 15MB) 임베딩이 CPU 병목의 원인 중 하나. Worker CPU 상향(256→1024)으로 완화했으나, 경량 폰트로의 전환은 미착수.
- OCR 구조화에 Haiku 등 경량 모델 사용 검토도 미착수(종료 임박 시점 리스크로 보류).

**원본**: `docs/infra/worker-sizing.md`

---

## 3. 데이터 모델

### confidence 컬럼 타입 잔여 정렬

`timeline_events.confidence`는 `Numeric(5,4)` → `String(10)`으로 수정했지만(트러블슈팅 3-1 참고), 같은 타입 문제를 가진 컬럼이 4개 더 있다: `evidences.confidence`, `evidence_texts.confidence`, `analysis_results` 계열 confidence, `evidence_relations.confidence`. 현재는 ORM으로 값을 안 써서 안 터지지만, 실제로 쓰기 시작하면 동일 에러가 재발할 수 있다.

### 모델 ↔ Alembic 마이그레이션 드리프트

`alembic/versions`의 마이그레이션에 `confidence` 계열 컬럼 정의가 없어(grep 0건), 실 RDS에 마이그레이션으로 스키마를 올릴 때 모델과 어긋날 수 있다. DB 통합 작업 시 마이그레이션을 모델 기준으로 재생성/정렬 필요.

**원본**: `docs/troubleshooting/timeline-confidence-type.md`, `docs/architecture/agent-feature-brief.md`

---

## 4. 인프라 — Well-Architected 잔여 리스크

> Well-Architected Tool 1차 리뷰(57문항): High 30 / Medium 24 / None 3. 대부분 MVP/dev 환경에서
> 일정·비용을 우선해 의도적으로 미룬 항목이며, 이후 상당수가 처리 완료됐다. 남은 것 위주로 정리.

| 항목 | Pillar | 상태 |
|---|---|---|
| Terraform state 3분할 (network/data/compute) | Operational Excellence | **의도적 보류** — state mv 위험 대비 종료 임박 시점 실익 낮음 |
| ECR Critical/High 취약점 잔여 | Security | **부분 완료** — 저위험 범프 다수 해소, `fastapi+starlette` 메이저·`weasyprint+pillow` 메이저는 별도 PR 필요 |
| Dependency scan 하드 게이트 전환 | Security | pip-audit CI 추가 완료(non-blocking) — 리포트 축적 후 하드 게이트 전환은 남음 |
| RDS restore rehearsal 실측 | Reliability | 절차·워크시트 문서화 완료 — 실제 타임드 리허설 실행은 남음 |
| Grafana 이메일 실수신 확인 | Operational Excellence | Contact Point/Rule 구성 완료 — 실제 수신함 기준 검증은 운영 중 확인 필요 |

**원본**: `docs/infra/implementation-status.md` §6~8, `aidlc-docs/remaining-tasks-20260702.md` 카테고리 B

---

## 5. 의도적으로 보류한 것

> 종료 일정(2026-07-10)·비용 대비 위험이 가치를 초과한다고 판단해 보류. 왜 보류했는지 근거를 남긴다.

| 항목 | 보류 사유 |
|---|---|
| Terraform 3분할 (위 4번과 동일) | state mv 위험, 종료 임박 |
| CloudFront 정적 캐싱 | 웹 프론트(Frontend ECS) 제거로 실익 제한 |
| Blue/Green 배포(ECS CodeDeploy) | deployment circuit breaker 자동 롤백으로 충분 |
| Secrets 자동 로테이션 | rotation Lambda 필요, dev 환경 실익 낮음 |
| ElastiCache Redis / RDS Proxy | 트래픽 낮아 idle 비용만 발생 |
| Fargate Savings Plan(1년 약정) | 프로젝트 종료 예정이라 약정 리스크 |
| GPS 아카이빙 실제 구현(export·배치) | 설계·Terraform lifecycle 규칙만 선반영. 실 구현은 GPS 무결성 검증(`chain_hash`) 로직과 얽혀 회귀 위험 큼 + 데모 규모에서 발생 안 하는 문제 |

**원본**: `aidlc-docs/remaining-tasks-20260702.md` 카테고리 C, `.kiro/steering/architecture.md` §6

---

## 6. Phase 2/3 범위 밖 (제품 설계상 제외)

> MVP 스코프 자체에서 제외하기로 합의한 항목. 버그나 미완성이 아니라 "다음 단계 로드맵".

- 음성 전사 confidence 점수화, 충돌 이벤트 자동 감지
- 본격 RAG 챗봇(현재는 정적 FAQ 폴백)
- 16개국 다국어 완성도(현재 vi+en만 완성, 나머지는 골격만)
- 진정서 자동 제출, 노무사 매칭
- 주휴·야간수당 자동 판별(법적 판단 영역이라 의도적 제외)
- 멀티테넌트 SaaS화
- 네이티브 앱 백그라운드 위치추적(GPS는 현재 포그라운드만)
- GPS Fake 탐지 고도화(현재는 OS `is_mocked` 플래그만 신뢰)

**원본**: `.kiro/steering/product.md` §7

---

## 우선순위 제안 (발표 시 참고)

발표에서 "다음에 할 일"을 압축해서 말해야 한다면 이 순서를 권한다:

1. **법적 필수 4건**(1번 섹션) — 실서비스 전환의 최우선 조건, 데모에는 없어도 되지만 "알고 있다"는 걸 보여줘야 함
2. **에이전트 필터 정확도**(2번 섹션) — 데모 중 실제로 겪은 한계라 스토리텔링하기 좋음
3. **온디바이스 OCR 고도화** — 지금 폴백 방식의 명확한 개선 방향이 있어 로드맵으로 설명하기 쉬움
