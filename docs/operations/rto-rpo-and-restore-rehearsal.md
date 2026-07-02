# BADA RTO/RPO 정의 및 복원 리허설 측정 (B-1)

> 목적: 재해 복구 목표(RTO/RPO)를 **확정**하고, PITR/스냅샷 복원의 실제 소요 시간을
> 측정하는 리허설 절차와 워크시트를 제공한다.
> 기준: `bada-dev-postgres`(운영은 `bada-dev-postgres-multiaz`로 cutover 완료), PostgreSQL 16, `ap-northeast-2`
> 관련: `docs/runbooks/rds-recovery.md`(실행 런북), `docs/operations/sli-slo-definition.md`(SLO)

## 1. 배경

- `rds-recovery.md` §2에 RTO/RPO **초안**이 있으나 "복원 리허설로 실제 시간 측정 후 확정"으로 유보 상태였다.
- 2026-06-28 Multi-AZ **cutover 리허설**은 완료(row count/PostGIS/Alembic/canary 검증)됐으나, 이는 자동 failover 대비이고 **from-scratch 복원(PITR/스냅샷) 소요 시간**은 아직 정식 측정되지 않았다.
- 본 문서는 그 갭(B-1)을 닫기 위한 확정 목표 + 측정 워크시트다.

## 2. 확정 RTO/RPO 목표 (dev/데모 기준)

| 지표 | 목표 | 근거 |
|---|---|---|
| **RPO** | ≤ 24시간 (가능 시 장애 직전 PITR ≈ 5분) | 7일 자동 백업 + PITR. 데모 환경 데이터 변경량 적음 |
| **RTO** | ≤ 2시간 | 스냅샷/PITR 복원 + Secret 전환 + ECS 재배포 + 검증 포함 |
| 가용성 SLO 연계 | ≥ 99% (7일) | `sli-slo-definition.md`. Multi-AZ 적용으로 상향(99.9%) 검토 가능 |

> Multi-AZ 자동 failover는 별도 경로(RTO 30~60초, RPO ≈ 0). 위 RTO/RPO는 **논리적 손상·오삭제·리전 스냅샷 복원** 등 failover로 못 막는 시나리오 기준이다.

### 시나리오별 복구 경로

| 시나리오 | 1차 대응 | 예상 RTO | RPO |
|---|---|---|---|
| AZ 장애 | Multi-AZ 자동 failover | 30~60초 | ≈ 0 |
| 인스턴스 손상 | 최신 자동 스냅샷/PITR 복원 | ≤ 2시간 | ≤ 24h (PITR 시 ≈ 5분) |
| 논리적 오삭제 | 사고 직전 시점 PITR 복원 | ≤ 2시간 | 사고 시점까지 |
| 광역(리전) 장애 | (보류) 스냅샷 타 리전 복사 — DR Phase 5 | 문서화만 | — |

## 3. 복원 리허설 절차 (실측용)

> ⚠️ 운영 DB는 건드리지 않는다. 리허설은 **신규 임시 인스턴스**로 복원해 시간만 측정하고 삭제한다.
> 실행은 인프라 담당자가 점검 창구에서 수행. 각 단계 시작/종료 시각을 §4 워크시트에 기록.

### 3.1 복원 시점 확인
```bash
aws rds describe-db-instances --region ap-northeast-2 \
  --db-instance-identifier bada-dev-postgres-multiaz \
  --query 'DBInstances[0].LatestRestorableTime'
```

### 3.2 PITR 복원 (타이머 시작)
```bash
# T0 기록 후 실행
aws rds restore-db-instance-to-point-in-time --region ap-northeast-2 \
  --source-db-instance-identifier bada-dev-postgres-multiaz \
  --target-db-instance-identifier bada-dev-postgres-rehearsal-restore-<date> \
  --use-latest-restorable-time \
  --db-instance-class db.t4g.micro \
  --db-subnet-group-name bada-dev-db-subnet-group \
  --vpc-security-group-ids <rds-sg-id> \
  --no-multi-az --no-publicly-accessible

aws rds wait db-instance-available --region ap-northeast-2 \
  --db-instance-identifier bada-dev-postgres-rehearsal-restore-<date>
# available 도달 시각 = T1 (복원 소요 = T1 - T0)
```

### 3.3 무결성 검증 (T1~T2)
- 테이블 수 / 주요 row count 비교
- `SELECT PostGIS_Version();`, Alembic revision 일치
- 핵심 SELECT 스모크

### 3.4 (선택) 연결 전환 시뮬레이션 (T2~T3)
> 실제 Secret 전환은 하지 않고, canary task로 신규 endpoint 접속만 측정.
- Backend/Worker 일회성 canary task로 신규 endpoint 접속 + read smoke

### 3.5 정리
```bash
aws rds delete-db-instance --region ap-northeast-2 \
  --db-instance-identifier bada-dev-postgres-rehearsal-restore-<date> \
  --skip-final-snapshot
```

## 4. 측정 워크시트 (담당자 기입)

| 구간 | 단계 | 시작(T) | 종료(T) | 소요 | 비고 |
|---|---|---|---|---|---|
| A | PITR 복원 요청 → available | T0 | T1 | | RTO 핵심 구간 |
| B | 무결성 검증 | T1 | T2 | | row/PostGIS/Alembic |
| C | canary 접속 검증 | T2 | T3 | | (선택) |
| — | **합계 (실측 RTO 추정)** | T0 | T3 | | 목표 ≤ 2h 대비 |

측정 후:
- 실측 RTO가 목표(≤2h)를 만족하면 §2 확정값 유지.
- 초과 시: 인스턴스 클래스 상향 또는 스냅샷 사전 준비 등 개선안 기록.

리허설 결과 기록란:
```text
리허설 일자   :
복원 소요(A)  :
검증 소요(B)  :
실측 RTO 추정 :
판정          : (목표 충족 / 개선 필요)
개선 액션     :
```

## 5. 실행 승인 조건

- 팀이 §2 RTO/RPO 목표 승인
- 점검 창구 확보 (운영 무영향, 신규 임시 인스턴스만 사용)
- 리허설 인스턴스 종료(삭제)까지 담당자 책임 명시 — 비용 리소스 잔존 방지
- 결과를 본 문서 §4에 기록 후 `implementation-status.md` P1 항목 갱신

## 6. 종료(7/10) 연동

- 리허설 임시 인스턴스는 측정 직후 `delete-db-instance --skip-final-snapshot`로 즉시 삭제 (비용 잔존 금지).
- 본 문서는 산출물로 보존 (포트폴리오: "RTO/RPO 정의 + 복원 리허설 실측" 근거).
