"""가드레일 테스트 — 단정 표현이 안전 표현으로 치환되는지."""
from rules.guardrails import has_forbidden, sanitize


def test_replaces_illegal():
    assert "불법" not in sanitize("이건 불법입니다.")
    assert "확인이 필요" in sanitize("이건 불법입니다.")


def test_replaces_confirmed_unpaid():
    out = sanitize("40만원 체불이 확정됩니다.")
    assert "확정" not in out
    assert "의심" in out


def test_replaces_guarantee_and_report():
    assert "무조건" not in sanitize("무조건 받을 수 있습니다.")
    assert "바로 신고" not in sanitize("바로 신고하세요.")


def test_clean_text_unchanged():
    s = "급여와 입금액 사이에 차이가 확인됩니다. 확인이 필요합니다."
    assert sanitize(s) == s
    assert has_forbidden(s) is False


def test_flag_detects_residual():
    assert has_forbidden("이건 불법입니다") is True
    assert has_forbidden(sanitize("이건 불법입니다")) is False
