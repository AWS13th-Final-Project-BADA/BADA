"""증거 대조(검증 포인트) 테스트."""
from rules.compare import compare


def test_wage_match_and_net_mismatch():
    evs = [
        {"category": "contract", "entities": {"hourly_wage": 10350}},
        {"category": "statement", "entities": {"hourly_wage": 10350,
            "amounts": [{"label": "실지급액", "value": 186300}]}},
        {"category": "payment", "entities": {"amounts": [{"label": "입금", "value": 150000}]}},
    ]
    pts = {p["key"]: p for p in compare(evs)}
    assert pts["hourly_wage"]["status"] == "match"
    assert pts["net_vs_deposit"]["status"] == "mismatch"
    assert pts["net_vs_deposit"]["values"]["차액"] == 36300


def test_wage_mismatch():
    evs = [
        {"category": "contract", "entities": {"hourly_wage": 10350}},
        {"category": "statement", "entities": {"hourly_wage": 9000}},
    ]
    pts = {p["key"]: p for p in compare(evs)}
    assert pts["hourly_wage"]["status"] == "mismatch"
    assert "확인이 필요" in pts["hourly_wage"]["note"]


def test_net_match():
    evs = [
        {"category": "statement", "entities": {"amounts": [{"label": "실지급액", "value": 186300}]}},
        {"category": "payment", "entities": {"amounts": [{"label": "입금", "value": 186300}]}},
    ]
    pts = {p["key"]: p for p in compare(evs)}
    assert pts["net_vs_deposit"]["status"] == "match"


def test_missing_one_side():
    evs = [{"category": "statement", "entities": {"hourly_wage": 10350}}]
    pts = {p["key"]: p for p in compare(evs)}
    assert pts["hourly_wage"]["status"] == "missing"
