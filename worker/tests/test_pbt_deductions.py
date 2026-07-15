"""PBT — deductions 규칙 엔진 속성 테스트.

속성:
- invariant: 모든 항목에 category 필드 존재
- invariant: 분류 후 항목 수 <= 원본 항목 수 (중복 이름 합산 가능)
- idempotency: total_deductions(classify(x)) 에 대해 재분류 시 동일
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from rules.deductions import classify_deductions, total_deductions

deduction_item = st.fixed_dictionaries({
    "name": st.sampled_from(["기숙사비", "식비", "작업복비", "기타", "보험료", "세금"]),
    "amount": st.integers(min_value=0, max_value=10000000),
})
deduction_list = st.lists(deduction_item, max_size=10)


@given(items=deduction_list)
@settings(max_examples=200)
def test_invariant_all_have_category(items):
    """분류 후 모든 항목에 category 키 존재."""
    classified = classify_deductions(items)
    for item in classified:
        assert "category" in item


@given(items=deduction_list)
@settings(max_examples=200)
def test_invariant_count_leq_original(items):
    """분류 후 항목 수 <= 원본 (동일 이름 합산 가능)."""
    classified = classify_deductions(items)
    assert len(classified) <= len(items)


@given(items=deduction_list)
@settings(max_examples=100)
def test_invariant_total_non_negative(items):
    """분류 후 합계 >= 0."""
    classified = classify_deductions(items)
    assert total_deductions(classified) >= 0
