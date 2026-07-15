# 단위 테스트 지침서

## Backend 테스트

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

**예상 결과:** 47 passed

**커버리지:**
- API 엔드포인트 (cases, evidences, analysis, community, auth)
- OCR 서비스, RAG, guardrails, language, terminology
- Cognito 인증 서비스

---

## Worker 테스트

```bash
cd worker
pip install -r requirements.txt
pytest -q
```

**예상 결과:** 168 passed (기존 155 + PBT 13)

**커버리지:**
- 규칙 엔진: wage, deductions, geofence, compare, legal, guardrails, confidence, sanity
- PBT: wage invariants, deductions invariants, geofence invariants, guardrails idempotency
- 서비스: timeline, translation, evidence_intake, transcribe_mode
- 프로바이더: OCR, schema

---

## Worker PBT 테스트 (Hypothesis)

```bash
cd worker
pytest tests/test_pbt_*.py -v --hypothesis-seed=0
```

**시드 재현:** 실패 시 출력되는 시드로 재실행:
```bash
pytest tests/test_pbt_wage.py --hypothesis-seed=<SEED>
```

---

## Eval Harness (OCR 정확도 회귀)

```bash
cd eval
python harness.py dataset/samples
```

**목적:** OCR 추출 결과가 골든 데이터셋 대비 정확도 유지 확인

---

## CI에서 실행 (GitHub Actions)

`.github/workflows/ci.yml`에서 push/PR 시 자동 실행:
1. Backend pytest
2. Worker pytest (PBT 포함)
3. Eval harness
