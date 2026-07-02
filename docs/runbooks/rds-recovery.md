# BADA RDS 복구·암호화 전환·Multi-AZ 리허설 런북

> 대상: `bada-dev-postgres`, PostgreSQL 16, `ap-northeast-2`
> 기준일: 2026-06-28
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

또한 현재 운영 DB는 Single-AZ이므로, 멘토 피드백에 따라 운영 DB를 직접 수정하지 않고 별도 Multi-AZ 인스턴스를 생성해 리허설 후 cutover 여부를 판단한다.

## 2. 제안 RTO/RPO

| 지표 | 값 | 근거 |
| --- | --- | --- |
| RPO | ≤ 24시간 (가능 시 장애 직전 PITR ≈ 5분) | 7일 자동 백업 + PITR |
| RTO | ≤ 2시간 | snapshot/PITR 복원, Secret 전환, ECS 재배포와 검증 시간 포함 |

> RTO/RPO 확정값·시나리오별 복구 경로·복원 리허설 측정 워크시트는 **단일 출처**
> `docs/operations/rto-rpo-and-restore-rehearsal.md`를 참조한다. 이 런북은 실행 절차(아래)에 집중한다.

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

## 5. Week 4 Multi-AZ 리허설 절차

핵심 원칙:

- 현재 운영 DB `bada-dev-postgres`는 건드리지 않는다.
- Terraform은 기본 운영 DB와 별개로 `enable_rehearsal_multiaz_db=true` 상태에서 리허설 DB를 유지한다.
- 리허설 DB는 `bada-dev-postgres-multiaz`, `storage_encrypted=true`, `multi_az=true` 기준이다.
- 실패하면 `DATABASE_URL`을 바꾸지 않고 리허설 DB만 삭제한다.

### 5.1 Terraform 생성 단계

```bash
cd infra
terraform plan -var-file="terraform.tfvars" \
  -var 'enable_rehearsal_multiaz_db=true'

terraform apply -var-file="terraform.tfvars" \
  -var 'enable_rehearsal_multiaz_db=true'
```

성공 기준:

- 기존 `aws_db_instance.postgres`는 변경 없음
- 신규 `aws_db_instance.postgres_rehearsal[0]`만 생성
- output `rds_rehearsal_endpoint`가 채워짐

### 5.2 접속 및 데이터 복원

기존 운영 DB와 리허설 DB를 각각 다른 로컬 포트로 포워딩한다.

```bash
terraform output -raw ssm_db_port_forward_command
terraform output -raw ssm_db_rehearsal_port_forward_command
```

예시 흐름:

```bash
pg_dump -h 127.0.0.1 -p 15432 -U bada_admin -d bada -Fc -f bada.dump
createdb -h 127.0.0.1 -p 15433 -U bada_admin bada
psql -h 127.0.0.1 -p 15433 -U bada_admin -d bada -c "CREATE EXTENSION IF NOT EXISTS postgis;"
pg_restore -h 127.0.0.1 -p 15433 -U bada_admin -d bada --clean --if-exists bada.dump
```

검증:

- 테이블 수, 주요 row count 비교
- `SELECT PostGIS_Version();`
- Alembic version 일치
- 핵심 SELECT/INSERT 스모크 테스트

2026-06-28 리허설 결과:

- `bada-dev-postgres-multiaz` 생성 완료: `MultiAZ=true`, `StorageEncrypted=true`, `available`
- 기존 운영 DB와 리허설 DB의 public base table 32개 row count 일치
- PostGIS `3.4`, Alembic `20260616_0004` 일치
- 리허설 DB temp table insert 후 rollback smoke 통과
- Backend/Worker 일회성 canary task로 새 DB 접속, Alembic/PostGIS, write/read smoke 통과
- 최종 dump/restore 재수행 후 public base table 32개 row count 재일치
- Secrets Manager `database_url`을 새 Multi-AZ DB endpoint로 전환
- Backend/Worker `force-new-deployment` 후 service stable, `/health` 200, 최근 로그 에러 패턴 없음
- Terraform `plan` 결과 `No changes`

### 5.3 cutover 전 최종 점검

- 점검 창구 확보
- Backend 쓰기 요청 최소화
- Worker queue 유입 일시 통제 여부 결정
- 최신 dump 기준으로 차이 재반영

### 5.4 cutover

1. Secrets Manager `database_url`을 리허설 DB endpoint로 교체
2. Backend / Worker `force-new-deployment`
3. `/health`, 보호 API, 업로드, 분석, PDF 검증
4. CloudWatch Logs / Alarm / SQS / RDS 에러 확인

### 5.5 rollback

문제 발생 시:

```text
use_rehearsal_multiaz_db_as_app_db=false로 Terraform apply
→ Backend / Worker force-new-deployment
→ /health / SQS consumer / 핵심 API 재검증
→ 리허설 DB는 즉시 삭제하지 말고 원인 분석 후 정리
```

## 6. 전환 검증

- 신규 endpoint가 private subnet과 기존 RDS Security Group을 사용
- SSL 연결 성공
- Alembic revision과 실제 schema 일치
- 사건·증거·분석 결과 건수 표본 확인
- Backend `/health` 200
- Worker consumer 시작 및 SQS 처리
- 업로드→분석→PDF E2E
- CloudWatch에 `AccessDenied`, DB timeout, connection refused 없음

## 7. 롤백

신규 RDS 전환 후 장애가 발생하면 기존 RDS가 보존된 동안 다음 순서로 복구한다.

```text
Backend·Worker 처리 중단
→ Secrets Manager database_url을 기존 endpoint로 복원
→ Backend·Worker 새 Task 배포
→ health·consumer·데이터 검증
→ 실패 신규 RDS는 원인 분석 전 삭제하지 않음
```

전환 중 양쪽 DB에 쓰기가 발생하면 데이터가 갈라질 수 있다. 전환 창에는 쓰기 중단 또는 Queue 유입 통제가 필요하다.

## 8. 실행 승인 조건

- 팀이 RTO/RPO와 점검 시간을 승인
- 최신 snapshot과 복원 경로 확인
- RDS 전용 KMS Key 준비
- Secret 변경 담당자와 rollback 담당자 지정
- 테스트 계정·사건·업로드 파일 준비
- 전환 전후 검증 체크리스트 공유
