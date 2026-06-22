"""PBT — guardrails 규칙 엔진 속성 테스트.

속성:
- idempotency: sanitize(sanitize(x)) == sanitize(x)
- invariant: sanitize 결과에 금지 표현 없음
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from rules.guardrails import sanitize

korean_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=0, max_size=200,
)


@given(text=korean_text)
@settings(max_examples=200)
def test_idempotency(text):
    """sanitize 2번 적용 = 1번 적용."""
    once = sanitize(text)
    twice = sanitize(once)
    assert once == twice


@given(text=korean_text)
@settings(max_examples=200)
def test_invariant_no_forbidden_expressions(text):
    """sanitize 결과에 금지 표현이 없어야 함."""
    result = sanitize(text)
    forbidden = ["불법입니다", "위법입니다", "체불이 확정", "무조건 받을 수",
                 "바로 신고하세요", "사업주가 처벌"]
    for f in forbidden:
        assert f not in result
