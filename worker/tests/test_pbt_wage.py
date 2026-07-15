"""PBT — wage 규칙 엔진 속성 테스트.

속성:
- invariant: hours가 있을 때, suspected_unpaid = total_expected - total_received
- invariant: hours가 비어있으면 결과는 None (계산 불가)
- idempotency: compute_unpaid(same inputs) == compute_unpaid(same inputs)
"""
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from rules.wage import compute_unpaid

hourly_wage = st.integers(min_value=1000, max_value=100000)
worked_hours = st.lists(st.floats(min_value=0.5, max_value=24, allow_nan=False, allow_infinity=False), min_size=1, max_size=31)
deposits = st.lists(st.integers(min_value=0, max_value=50000000), max_size=10)


@given(wage=hourly_wage, hours=worked_hours, deps=deposits)
@settings(max_examples=200)
def test_invariant_suspected_equals_expected_minus_received(wage, hours, deps):
    """hours가 있을 때: 미지급의심 = 기대급여 - 실수령."""
    result = compute_unpaid(wage, hours, deps)
    if result.total_expected_wage is not None and result.total_received_wage is not None:
        assert result.suspected_unpaid == result.total_expected_wage - result.total_received_wage


@given(wage=hourly_wage, hours=worked_hours, deps=deposits)
@settings(max_examples=200)
def test_invariant_non_negative_expected(wage, hours, deps):
    """hours가 있을 때 기대급여 >= 0."""
    result = compute_unpaid(wage, hours, deps)
    if result.total_expected_wage is not None:
        assert result.total_expected_wage >= 0


@given(wage=hourly_wage, deps=deposits)
@settings(max_examples=50)
def test_empty_hours_returns_none_or_zero(wage, deps):
    """hours 비어있으면 기대급여는 None 또는 0."""
    result = compute_unpaid(wage, [], deps)
    assert result.total_expected_wage is None or result.total_expected_wage == 0


@given(wage=hourly_wage, hours=worked_hours, deps=deposits)
@settings(max_examples=50)
def test_idempotency(wage, hours, deps):
    """같은 입력이면 같은 결과."""
    r1 = compute_unpaid(wage, hours, deps)
    r2 = compute_unpaid(wage, hours, deps)
    assert r1.suspected_unpaid == r2.suspected_unpaid
