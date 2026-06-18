# 트러블슈팅 — `/analyze` 저장 시 `could not convert string to float: 'high'`

> 작성일: 2026-06-16
> 영향 범위: backend `/cases/{id}/analyze` (타임라인 저장) · CI "Backend API tests"
> 결론: 모델 컬럼 타입 오류(스키마 정의 버그). 1줄 수정으로 해결. 데이터/마이그레이션 영향 없음.

---

## 1. 증상

GitHub Actions CI의 **Backend API tests** 단계에서 5개 테스트 실패:

- `tests/test_analyze_ocr.py::test_analyze_uses_ocr_entities`
- `tests/test_analyze_ocr.py::test_analyze_persists_and_report`
- `tests/test_api.py::test_full_flow`
- `tests/test_api.py::test_persistence_endpoints`
- `tests/test_api.py::test_missing_when_no_evidence`

공통 에러:

```
sqlalchemy.exc.StatementError: (builtins.ValueError) could not convert string to float: 'high'
[SQL: INSERT INTO timeline_events (... confidence ...) VALUES (...)]
```

다섯 개 모두 `POST /cases/{id}/analyze` 호출 → `app/routers/analysis.py`의 `db.commit()` 지점에서 터짐.

---

## 2. 원인

**모델 컬럼 타입과 실제 저장 값의 불일치.**

`backend/app/models.py`의 `TimelineEvent.confidence`가 숫자 컬럼으로 정의돼 있었음:

```python
confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))   # ← 잘못된 타입
```

그러나 코드는 여기에 문자열 enum을 넣음 — `app/routers/analysis.py`:

```python
db.add(TimelineEvent(..., confidence=e.get("confidence", "medium")))   # "high" / "medium" / "low"
```

`commit()` → flush 시 SQLite가 `Numeric` 컬럼에 들어온 `'high'`를 float으로 변환하려다 `ValueError` 발생.

### 왜 코드가 아니라 모델이 틀린 건가
- `domain.md` 스펙: `timeline_events.confidence`는 `high / medium / low` **enum 문자열**.
- `schemas.py` / `schemas_report.py`도 이미 전부 문자열로 정의됨:
  - `Confidence = Literal["high", "medium", "low"]`
  - `class Confidence(str, Enum): high/medium/low`
- `product.md`: confidence **점수화(숫자)** 는 MVP 범위 밖(Phase 2).

즉 MVP의 confidence는 문자열 enum이 맞고, 모델만 과거 설계의 `Numeric(5,4)`로 남아 있던 것.

### 왜 로컬/CI에서 이제야 터졌나
- 테스트는 `conftest.py`에서 `Base.metadata.create_all`로 **모델 정의로부터** 테이블을 생성 → 모델의 `Numeric`이 그대로 사용됨.
- 마이그레이션(`alembic/versions`)에는 `confidence` 컬럼 정의가 아예 없음(grep 0건) → 모델 ↔ 마이그레이션 드리프트도 별도로 존재(아래 5번 참고).

---

## 3. 진단 과정

1. 스택트레이스 최하단 확인 → `to_float` 변환에서 `'high'` 실패.
2. 실패 SQL이 `INSERT INTO timeline_events ... confidence ...` 임을 확인.
3. `models.py`에서 `TimelineEvent.confidence = Numeric(5,4)` 발견.
4. `analysis.py`에서 문자열 `"medium"` 등을 넣는 것 확인.
5. `domain.md` / `schemas.py`로 "원래 문자열 enum이 맞다"는 근거 확보 → 모델이 틀렸다고 판단.

---

## 4. 조치 (적용 완료)

`backend/app/models.py` — `TimelineEvent.confidence` 타입을 문자열로 변경:

```python
# 변경 전
confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))

# 변경 후
# confidence는 high/medium/low enum 문자열(domain.md). 점수화(Numeric)는 Phase 2.
confidence: Mapped[str | None] = mapped_column(String(10))
```

### 검증
```
cd backend
pytest -q
# 변경 전: 5 failed, 27 passed
# 변경 후: 32 passed
```

### 영향 범위 / 위험
- 라이브 RDS가 아직 없고, 테스트는 모델에서 테이블을 새로 생성 → **데이터 이관·마이그레이션 영향 없음**.
- 코드 변경은 모델 1줄. 다른 로직 수정 없음.

---

## 5. 남은 잠재 이슈 (이번엔 안 고침 — 후속 과제)

같은 `Numeric(5,4)` 타입의 confidence 컬럼이 4개 더 있음:

| 모델/테이블 | 현재 ORM으로 값 기록? |
|---|---|
| `evidences.confidence` | 아니오 |
| `evidence_texts.confidence` | 아니오 |
| `analysis_results` 계열 `confidence` | 아니오 |
| `evidence_relations.confidence` | 아니오 |

- 현재 이 컬럼들엔 ORM으로 값을 쓰지 않아 **지금은 안 터짐**.
- 하지만 confidence를 문자열 enum으로 쓰기로 했으므로(domain.md), 이 테이블들에 값을 저장하기 시작하면 같은 에러가 재발할 수 있음.
- 권장: 해당 테이블을 실제로 사용할 때(또는 DB 통합 작업 시) 함께 `String`으로 정렬.

### 모델 ↔ 마이그레이션 드리프트
- `alembic/versions`의 마이그레이션에 `timeline_events.confidence`(및 다른 confidence) 컬럼이 정의돼 있지 않음.
- 실제 RDS에 마이그레이션으로 스키마를 올릴 때 모델과 어긋날 수 있으므로, DB 통합 단계에서 마이그레이션을 모델 기준으로 재생성/정렬 필요.

---

## 6. 한 줄 요약

`timeline_events.confidence`가 `Numeric`이라 문자열 enum(`high/medium/low`)을 못 받아 `/analyze`가 깨졌다. domain.md 스펙대로 `String`으로 바꿔 해결. 나머지 confidence 컬럼과 마이그레이션 정렬은 DB 통합 때 후속 처리.
