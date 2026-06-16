# 트랜잭션 (Transaction)

## 트랜잭션이란?

트랜잭션은 **데이터베이스에서 하나의 논리적 작업 단위**를 구성하는 일련의 연산들이다.  
"전부 성공하거나, 전부 실패하거나" — 중간 상태는 허용하지 않는다.

### 대표 예시: 계좌 이체

```
A 계좌에서 10만원 출금  →  B 계좌에 10만원 입금
```

출금은 성공했는데 입금이 실패하면? → 10만원이 사라진다.  
트랜잭션은 이 두 연산을 하나로 묶어 **둘 다 성공하거나 둘 다 취소**되도록 보장한다.

---

## ACID 특성

ACID는 트랜잭션이 안전하게 처리되기 위해 보장해야 할 4가지 속성이다.

### 1. 원자성 (Atomicity)

> "트랜잭션 내의 모든 연산은 전부 실행되거나 전부 실행되지 않아야 한다."

- 트랜잭션 중간에 오류가 발생하면, 이미 실행된 연산도 **모두 롤백(Rollback)** 된다.
- **"All or Nothing"** 원칙.

```
BEGIN;
  UPDATE accounts SET balance = balance - 100000 WHERE id = 'A';  -- 성공
  UPDATE accounts SET balance = balance + 100000 WHERE id = 'B';  -- 실패 ← 여기서 오류
ROLLBACK;  -- A의 차감도 취소됨
```

### 2. 일관성 (Consistency)

> "트랜잭션 실행 전후로 데이터베이스는 항상 일관된 상태를 유지해야 한다."

- 트랜잭션이 완료되어도 **무결성 제약 조건(Constraints)** 이 항상 만족되어야 한다.
- 예: 잔액이 음수가 되면 안 된다는 규칙이 있으면, 어떤 트랜잭션도 그 규칙을 깰 수 없다.

```
-- 잔액 >= 0 제약이 있는 경우
UPDATE accounts SET balance = balance - 1000000 WHERE id = 'A';
-- A의 잔액이 500,000원이면 → 제약 위반 → 트랜잭션 거부
```

### 3. 격리성 (Isolation)

> "동시에 실행 중인 트랜잭션들은 서로의 중간 상태를 볼 수 없어야 한다."

- 각 트랜잭션은 다른 트랜잭션이 없는 것처럼 독립적으로 실행되어야 한다.
- 격리성을 완벽히 보장할수록 성능은 낮아지는 **트레이드오프** 관계다.

#### 격리 수준 (Isolation Level)

| 격리 수준 | Dirty Read | Non-Repeatable Read | Phantom Read |
|-----------|:----------:|:-------------------:|:------------:|
| READ UNCOMMITTED | 발생 | 발생 | 발생 |
| READ COMMITTED   | 방지 | 발생 | 발생 |
| REPEATABLE READ  | 방지 | 방지 | 발생 |
| SERIALIZABLE     | 방지 | 방지 | 방지 |

> **용어 설명**
> - **Dirty Read**: 커밋되지 않은 데이터를 다른 트랜잭션이 읽는 현상
> - **Non-Repeatable Read**: 같은 쿼리를 두 번 실행했을 때 결과가 달라지는 현상
> - **Phantom Read**: 같은 조건의 쿼리를 두 번 실행했을 때 없던 행이 생기는 현상

### 4. 지속성 (Durability)

> "성공적으로 커밋된 트랜잭션의 결과는 시스템 장애가 발생해도 영구적으로 보존되어야 한다."

- 커밋 완료 후 서버가 다운되어도 데이터는 사라지지 않는다.
- **WAL(Write-Ahead Log)** 등의 기법으로 구현한다.

---

## 트랜잭션의 상태 변화

트랜잭션은 생성부터 종료까지 다음 5가지 상태를 거친다.

```
                  ┌─────────────────────────────────────────┐
                  │                                         │
   시작           │  오류/실패                               │
   ──────► Active ──────────────► Failed ──────► Aborted   │
            │                                    (Rollback  │
            │ 마지막 연산 완료                    완료)       │
            ▼                                               │
        Partially                                           │
        Committed ─────────────────────────────► Committed │
                     커밋 성공 (디스크 반영 완료)            │
                                                           │
                  └─────────────────────────────────────────┘
```

### 상태 설명

| 상태 | 설명 |
|------|------|
| **Active** | 트랜잭션이 시작되어 연산들이 실행 중인 상태 |
| **Partially Committed** | 마지막 연산까지 완료됐으나, 아직 디스크에 완전히 반영되지 않은 상태 |
| **Failed** | 실행 중 오류가 발생하여 더 이상 진행할 수 없는 상태 |
| **Aborted** | 롤백이 완료되어 트랜잭션 시작 이전 상태로 되돌아간 상태 |
| **Committed** | 모든 연산이 성공적으로 완료되고 데이터베이스에 영구 반영된 상태 |

### 상태 전이 규칙

```
Active          → Partially Committed  : 마지막 연산 정상 완료
Active          → Failed               : 연산 중 오류 발생
Partially Committed → Committed        : 디스크 반영(COMMIT) 성공
Partially Committed → Failed           : 커밋 과정에서 오류 발생
Failed          → Aborted              : 롤백 완료
Aborted         → Active               : 트랜잭션 재시작 (선택적)
```

---

## COMMIT과 ROLLBACK

```sql
-- 기본 구조
BEGIN;                  -- 트랜잭션 시작 (Active)

  -- 연산들 실행
  UPDATE ...;
  INSERT ...;

COMMIT;                 -- 성공 시 영구 반영 (→ Committed)
-- 또는
ROLLBACK;               -- 실패 시 취소 (→ Aborted)
```

### SAVEPOINT (부분 롤백)

전체를 롤백하지 않고, 특정 지점까지만 되돌릴 수 있다.

```sql
BEGIN;
  UPDATE accounts SET balance = balance - 100000 WHERE id = 'A';
  SAVEPOINT after_debit;                  -- 중간 저장점

  UPDATE accounts SET balance = balance + 100000 WHERE id = 'B';
  -- 여기서 오류 발생 시
  ROLLBACK TO SAVEPOINT after_debit;      -- A의 출금은 유지, B의 입금만 취소

COMMIT;
```

---

## 동시성 문제와 트랜잭션

여러 트랜잭션이 동시에 실행될 때 발생할 수 있는 문제들이다.

### Lost Update (갱신 손실)
두 트랜잭션이 같은 데이터를 읽고 동시에 수정하면, 먼저 커밋한 트랜잭션의 변경이 사라진다.

```
T1: 잔액 읽기(1000) → 100 추가 → 1100 저장
T2: 잔액 읽기(1000) → 200 추가 → 1200 저장  ← T1의 +100이 사라짐
```

### Dirty Read
커밋되지 않은 데이터를 읽은 뒤, 그 트랜잭션이 롤백되면 없는 데이터를 기반으로 처리한 셈이 된다.

```
T1: 잔액 1000 → 2000으로 변경 (미커밋)
T2: 잔액 읽기 → 2000 (Dirty Read)
T1: ROLLBACK → 잔액 다시 1000
T2: 2000 기준으로 처리한 결과가 잘못됨
```

---

## 핵심 요약

```
트랜잭션 = 논리적 작업 단위 (All or Nothing)

ACID
├── Atomicity    → 전부 성공 OR 전부 실패
├── Consistency  → 무결성 제약 항상 유지
├── Isolation    → 동시 실행 트랜잭션 간 독립성
└── Durability   → 커밋 후 영구 보존

상태 흐름
Active → Partially Committed → Committed (정상)
Active → Failed → Aborted              (비정상)
```

---

## 참고

- [PostgreSQL Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [MySQL InnoDB Transaction Model](https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-model.html)
- Abraham Silberschatz, *Database System Concepts*, 7th Ed.
