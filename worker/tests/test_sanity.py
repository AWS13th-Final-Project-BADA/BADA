"""타당성 검사 테스트."""
from rules.sanity import check_entities


def test_통상임금_작으면_플래그():
    e = {"amounts": [{"label": "월 통상임금", "value": 2090000}, {"label": "기본급", "value": 2096900}]}
    w = check_entities(e)
    assert any(x["field"] == "통상임금/기본급" and x["level"] == "high" for x in w)


def test_정상이면_플래그_없음():
    e = {"amounts": [{"label": "월 통상임금", "value": 2096900}, {"label": "기본급", "value": 2090000}]}
    assert check_entities(e) == []


def test_실지급_초과_플래그():
    e = {"amounts": [{"label": "지급액 계", "value": 186300}, {"label": "실지급액", "value": 200000}]}
    assert any(x["field"] == "실지급액" for x in check_entities(e))


def test_명세서_산식_불일치():
    e = {"amounts": [{"label": "지급액 계", "value": 186300}, {"label": "공제액 계", "value": 50000},
                     {"label": "실지급액", "value": 186300}]}  # 186300-50000≠186300
    assert any(x["field"] == "명세서 산식" for x in check_entities(e))


def test_명세서_산식_정상():
    e = {"amounts": [{"label": "지급액 계", "value": 186300}, {"label": "공제액 계", "value": 0},
                     {"label": "실지급액", "value": 186300}]}
    assert not any(x["field"] == "명세서 산식" for x in check_entities(e))
