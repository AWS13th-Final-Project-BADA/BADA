"""법령 산식 매핑 테스트 — 최저임금/가산수당/과다공제."""
from rules import legal


def test_최저임금_미달_플래그():
    f = legal.check_minimum_wage(9000, hours_sum=200, year=2026)
    assert f and f["level"] == "high"
    assert f["shortfall_per_hour"] == 10320 - 9000
    assert f["shortfall_total"] == (10320 - 9000) * 200


def test_최저임금_충족_없음():
    assert legal.check_minimum_wage(10320, year=2026) is None
    assert legal.check_minimum_wage(12000, year=2026) is None


def test_연도별_최저임금():
    assert legal.min_hourly_wage(2025) == 10030
    assert legal.min_hourly_wage(2026) == 10320
    assert legal.min_hourly_wage() == 10320  # 최신


def test_가산수당_추정():
    f = legal.expected_premium_pay(10000, overtime_h=10, night_h=4, holiday_h=0)
    # 가산분 = 10000 * (10*0.5 + 4*0.5) = 10000*7 = 70000
    assert f["estimated_premium"] == 70000
    assert f["level"] == "medium"


def test_가산수당_없으면_None():
    assert legal.expected_premium_pay(10000, 0, 0, 0) is None
    assert legal.expected_premium_pay(None, 10) is None


def test_과다공제_플래그():
    # 월급 2,000,000 기준 국민연금 표준 4.5%=90,000. 200,000은 1.5배 초과 → 플래그
    out = legal.check_insurance_over_deduction(
        [{"name": "국민연금", "amount": 200000}], base_wage=2000000)
    assert out and out[0]["type"] == "insurance_over"


def test_정상공제_플래그_없음():
    out = legal.check_insurance_over_deduction(
        [{"name": "국민연금", "amount": 90000}], base_wage=2000000)
    assert out == []


def test_legal_review_통합():
    ctx = {
        "agreed_hourly_wage": 9000,
        "worked_hours": [100.0, 100.0],
        "raw_deductions": [{"name": "국민연금", "amount": 300000}],
        "evidence_entities": [
            {"entities": {"overtime_hours": 12, "monthly_wage": 1800000}},
        ],
    }
    r = legal.legal_review(ctx, {"calculation_detail": {"hours_sum": 200}})
    types = {f["type"] for f in r["findings"]}
    assert "minimum_wage" in types          # 9000 < 10320
    assert "premium_pay" in types           # 연장 12h
    assert "insurance_over" in types        # 30만 > 표준*1.5
    assert r["min_wage"] == 10320
