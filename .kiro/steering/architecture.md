---
inclusion: always
---

# BADA — 아키텍처 불변식 (Architecture Steering)

> 이 파일은 BADA의 가장 중요한 설계 불변식을 정의한다.
> 신뢰성·디버깅·법적 안전이 전부 여기 달려 있다. 어떤 기능을 구현하든 이 규칙을 깨면 안 된다.

## 1. 최상위 불변식 — 규칙/LLM 분리

> **계산·비교·정렬·판정은 규칙 기반 코드(설명 가능). 문장화·요약·OCR만 LLM.**

| LLM이 하는 것 (생성형 허용) | 규칙 기반 코드가 하는 것 (생성형 금지) |
| --- | --- |
| 이미지 OCR (텍스트/엔티티 추출) | **급여-입금 차액 계산** |
| 발화 분류 (지급약속/임의공제 통보 등) | **공제 항목 분류 (사전 매핑)** |
| 타임라인 문장 다듬기 | **타임라인 시간순 정렬** |
| 사건 요약 문장 | **누락 증거 체크리스트 판정** |
| 모국어 번역 보정 | **GPS 지오펜스 안/밖 판정 (ST_Contains)** |
| 쉬운 한국어 설명 | **GPS ↔ 카톡 교차검증 매칭** |

- 이유: "AI가 금액을 잘못 계산하면?"이라는 질문에 **"계산은 AI가 안 한다"**고 답할 수 있어야 한다.
- 원본 숫자는 **무수정 보존**한다. LLM은 명세서에서 "250,000"을 *읽어오기만* 하고, 차액은 규칙 코드가 계산.

## 2. LLM 출력은 항상 구조화 강제

- 모든 추출/분류 LLM 호출은 **Pydantic 스키마**로 출력을 강제한다.
- JSON 파싱 실패 / 스키마 검증 실패 시 → **재시도(최대 N회)**, 그래도 실패하면 `ocr_status='failed'`로 표기하고 사용자에게 "확인 필요" 노출. **임의로 값을 지어내지 않는다.**
- 추출값에는 `confidence(high/medium/low)`를 붙이고, low는 화면에 `확인 필요` 배지로 표시.

## 3. 분석 파이프라인 (단일 워커, 순차 단계)

SQS가 분석 작업을 받으면 워커가 아래 순서로 실행한다 (Step Functions 없이 코드로 순차).

```
process_case(case_id):
  1. 증거별 OCR + 엔티티 추출   → LLM (Vision/Upstage) + Pydantic
  2. 규칙 기반 차액·공제 계산    → 순수 Python (생성형 X)
  3. 번역 + 원문-번역 대조표     → Translate (원문 보존)
  4. 타임라인 = 규칙 정렬 + LLM 문장화 보조
  5. 누락 체크리스트            → 규칙 기반
  6. GPS 지오펜스 태깅 + 교차검증 → 규칙 기반 (PostGIS/shapely)
  7. Evidence Pack PDF 렌더     → WeasyPrint
  8. 결과 RDS 저장, PDF S3 저장, 상태=completed
```

## 4. Human-in-the-loop (검토 가능한 자동화)

완전 자동화보다 **검토 가능한 자동화**가 BADA에 적합하다. 아래 항목은 자동 확정하지 않고 사용자 검토 단계를 거친다.
- 애매한 날짜 (충돌/추정불가는 "후보"로 남김)
- 금액 단위 불명확 (월급/시급)
- 발화자 불분명 (사업주 발언 맞는지)
- 비식별화 누락 가능성
- confidence가 low인 모든 추출 항목

UI 패턴 예:
```
AI가 추출한 금액: 2,300,000원
이 금액이 급여명세서상 지급액이 맞나요?  [맞아요] [수정할래요]
```

## 5. 추적성 (Traceability)

- 모든 타임라인 이벤트·대조표 항목은 **원본 증거(source_evidence_id)에 링크**한다.
- AI 결과는 단순 텍스트가 아니라 **재분석·디버깅·품질측정이 가능한 구조화 데이터**로 RDS에 저장한다.
- 사용자 수정 이력을 보존한다 (원본 추출값 vs 수정값).

## 6. GPS 증거 신빙성 — 미완성 항목 (구현 필요)

> 아래는 설계는 완료됐으나 SQS 워커 진입점 코드가 없어 연결이 끝나지 않은 항목이다.

### pipeline.py 호출 시 gps_logs 구성 규칙
DB에서 GPS 로그를 꺼내 `ctx["gps_logs"]`에 담을 때 반드시 `is_delayed_upload` 필드를 포함해야 한다.
`geofence.tag_logs()`가 이 값을 보고 지연 업로드 핑을 교차검증에서 자동 배제한다.

```python
# SQS 워커 진입점에서 이렇게 구성해야 함
ctx["gps_logs"] = [
    {
        "ts": log.ts,
        "lat": float(log.lat),
        "lng": float(log.lng),
        "is_mocked": log.is_mocked,
        "is_delayed_upload": log.is_delayed_upload,  # ← 반드시 포함
    }
    for log in gps_logs
]
```

누락 시 지연 업로드 핑이 걸러지지 않고 교차검증 결과에 포함된다.

### chain_hash DB 마이그레이션 주의
`gps_logs.chain_hash`는 `nullable=False`. 기존 데이터가 있는 상태에서 마이그레이션 시
기존 행 처리 방식을 정해야 한다 (예: 빈 문자열 기본값 부여 후 제약 추가).
MVP 초기라 데이터가 없으면 해당 없음.

### GPS 로그 장기 아카이빙 (설계만 완료, 구현 보류)

> 재직 중 GPS 수집이 몇 달~몇 년 이어질 수 있어, RDS `gps_logs`에 무기한 누적하면
> 스토리지·백업 비용이 계속 늘어난다. 아래는 설계만 확정하고, 애플리케이션 코드는
> 아직 구현하지 않았다(Terraform lifecycle 규칙만 선반영 — `infra/data.tf`
> `gps-archive/` prefix).

**보존 정책 원칙**
- 완전 삭제 시점은 임금채권 소멸시효(3년) 기준. `gps_retention_days`(3년)로 일반
  데이터 `retention_days`(90일)와 분리 관리한다 — security.md 3항 참조.
- 3년 안에서도 "안 쓰는 구간은 저렴한 저장소로, 다시 쓸 땐 즉시 조회 가능"해야
  하므로 Glacier Flexible/Deep Archive(분~시간 지연)는 부적합. 실제 조회가
  보관 기간 내 한두 번뿐일 것으로 예상돼 S3 Standard-IA 단계도 건너뛰고
  **GLACIER_IR(즉시조회 가능한 Glacier)**로 바로 이관한다.

**아카이빙 트리거**
- 사건이 완료되고 GPS ping이 일정 기간(예: 14일) 없으면 "비활성"으로 간주,
  해당 사건의 `gps_logs`를 JSON으로 S3 `gps-archive/{case_id}.json`에 export.
- export 시 `/summary`의 `integrity.sha256`을 그대로 포함시켜, RDS 원본이
  삭제돼도 무결성 증명은 파일 자체로 유지되게 한다.

**구현 시 반드시 처리해야 할 위험 지점 (다음 단계 착수 시 참고)**
1. `/gps/verify`의 체인 검증이 RDS-S3 경계를 넘는 로그에 대해 prev_hash를
   이어서 검증하도록 로직 확장 필요 — 현재 `gps.py::verify_chain`은 단일
   소스(RDS)만 가정하고 있어 그대로 두면 아카이브된 사건에서 오탐 발생.
2. 읽기 경로 4곳(`/summary`, `/verify`, `/logs`, `report_builder.py`)에
   "RDS 미존재 시 S3 폴백" 추가 필요. 누락 시 아카이브된 사건의 Evidence Pack
   GPS 섹션이 비거나 에러.
3. "사건 비활성 감지" 배치의 실행 위치 — tech.md가 Step Functions를 금지하므로
   Worker의 주기 작업 또는 EventBridge + 경량 Lambda 중 선택 필요.

**보류 이유**: 데모 트래픽 규모에서는 RDS 부담이 실질적으로 발생하지 않고,
위 3항목이 GPS 무결성 검증이라는 핵심 기능을 직접 건드려 회귀 위험이 크다.

## 7. (MVP+) 챗봇 = 제한적 Agentic Workflow

완전 자율 Agent를 만들지 않는다. 도구 호출은 아래로 제한:
- 허용: 질문 분류 / 공식문서 검색(RAG 또는 정적 FAQ) / Evidence Pack 상태 확인 / 누락자료 안내 / 절차 안내 / 모국어 설명 / 전문가 확인 필요 안내
- 금지: 위법·체불·금액 확정 / 진정서 자동제출 / 노무사 대리 / 사업주 책임 단정
- 흐름: 언어감지 → 질문분류 → 법률판단 위험감지 → Pack 상태조회 → 문서검색 → 답변생성 → **출력단 Guardrails 필터** → 모국어 응답
- RAG가 기간 내 불안정하면 → **동일 지식베이스를 정적 다국어 FAQ로 폴백** (product.md 표현 정책 그대로 적용).
