# BADA RDS 복구·암호화 전환 런북

> 대상: `bada-dev-postgres`, PostgreSQL 16, `ap-northeast-2`
> 기준일: 2026-06-24
> 이 문서는 실행 계획이다. 실제 복원·전환은 팀 승인과 점검 시간 확보 후 수행한다.

## 1. 현재 상태

| 항목 | 값 |
| --- | --- |
| 상태 | `available` |
| 인스턴스 | `db.t4g.micro`, Single-AZ |
| 저장 암호화 | 미적용 |
| 자동 백업 | 7일 |
| PITR | 사용 가능 |
| 삭제 보호 | 활성 |
| 네트워크 | Private DB Subnet Group |

현재 자동 snapshot도 암호화되지 않는다. 기존 인스턴스의 저장 암호화는 인플레이스 변경할 수 없으므로 암호화 snapshot 복사와 신규 RDS 복원이 필요하다.

## 2. 제안 RTO/RPO

| 지표 | 제안 | 근거 |
| --- | --- | --- |
| RPO | 최대 24시간, 가능하면 장애 직전 PITR | MVP 데모 환경의 데이터 변경량과 7일 자동 백업 |
| RTO | 2시간 이내 | snapshot/PITR 복원, Secret 전환, ECS 재배포와 검증 시간 포함 |

이 값은 팀 승인 전 초안이다. 복원 리허설을 수행해 실제 시간을 측정한 뒤 확정한다.

## 3. 장애 복구 절차

### 3.1 복원 시점 결정

```bash
aws rds describe-db-instances \
  --region ap-northeast-2 \
  --db-instance-identifier bada-dev-postgres \
  --query 'DBInstances[0].LatestRestorableTime'

aws rds describe-db-snapshots \
  --region ap-northeast-2 \
  --db-instance-identifier bada-dev-postgres \
  --snapshot-type automated \
  --query 'reverse(sort_by(DBSnapshots,&SnapshotCreateTime))[:5].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
  --output table
```

### 3.2 신규 인스턴스 복원

복원 대상 이름은 기존 인스턴스와 겹치지 않게 지정한다.

```bash
aws rds restore-db-instance-to-point-in-time \
  --region ap-northeast-2 \
  --source-db-instance-identifier bada-dev-postgres \
  --target-db-instance-identifier bada-dev-postgres-restore-<date> \
  --use-latest-restorable-time \
  --db-instance-class db.t4g.micro \
  --db-subnet-group-name bada-dev-db-subnet-group \
  --vpc-security-group-ids sg-05ebefbe5fd702767 \
  --no-multi-az \
  --no-publicly-accessible
```

복원 인스턴스가 `available`이 될 때까지 기다린다.

```bash
aws rds wait db-instance-available \
  --region ap-northeast-2 \
  --db-instance-identifier bada-dev-postgres-restore-<date>
```

## 4. 암호화 마이그레이션 절차

1. Terraform으로 RDS 전용 KMS Key와 Alias를 준비한다.
2. 전환 직전 수동 snapshot을 생성한다.
3. snapshot을 RDS 전용 KMS Key로 암호화 복사한다.
4. 암호화 snapshot에서 신규 RDS를 복원한다.
5. DB 연결·schema·핵심 데이터와 애플리케이션 호환성을 검증한다.
6. Secrets Manager의 `database_url`을 신규 endpoint로 변경한다.
7. Backend·Worker Task를 새로 배포하고 E2E를 검증한다.
8. 안정화 기간 동안 기존 RDS를 보존한 뒤 승인 후 종료한다.

```bash
aws rds create-db-snapshot \
  --region ap-northeast-2 \
  --db-instance-identifier bada-dev-postgres \
  --db-snapshot-identifier bada-dev-postgres-pre-encryption-<date>

aws rds copy-db-snapshot \
  --region ap-northeast-2 \
  --source-db-snapshot-identifier <source-snapshot-arn> \
  --target-db-snapshot-identifier bada-dev-postgres-encrypted-<date> \
  --kms-key-id <rds-kms-key-arn>
```

복원 리소스는 최종적으로 Terraform state에 import하거나 코드로 재구성해 수동 리소스로 남기지 않는다.

## 5. 전환 검증

- 신규 endpoint가 private subnet과 기존 RDS Security Group을 사용
- SSL 연결 성공
- Alembic revision과 실제 schema 일치
- 사건·증거·분석 결과 건수 표본 확인
- Backend `/health` 200
- Worker consumer 시작 및 SQS 처리
- 업로드→분석→PDF E2E
- CloudWatch에 `AccessDenied`, DB timeout, connection refused 없음

## 6. 롤백

신규 RDS 전환 후 장애가 발생하면 기존 RDS가 보존된 동안 다음 순서로 복구한다.

```text
Backend·Worker 처리 중단
→ Secrets Manager database_url을 기존 endpoint로 복원
→ Backend·Worker 새 Task 배포
→ health·consumer·데이터 검증
→ 실패 신규 RDS는 원인 분석 전 삭제하지 않음
```

전환 중 양쪽 DB에 쓰기가 발생하면 데이터가 갈라질 수 있다. 전환 창에는 쓰기 중단 또는 Queue 유입 통제가 필요하다.

## 7. 실행 승인 조건

- 팀이 RTO/RPO와 점검 시간을 승인
- 최신 snapshot과 복원 경로 확인
- RDS 전용 KMS Key 준비
- Secret 변경 담당자와 rollback 담당자 지정
- 테스트 계정·사건·업로드 파일 준비
- 전환 전후 검증 체크리스트 공유
