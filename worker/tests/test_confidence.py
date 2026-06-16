"""근거 기반 confidence 테스트."""
from rules.confidence import assess


def test_sanity_연루_금액은_low():
    e = {"amounts": [{"label": "월 통상임금", "value": 2090000},
                     {"label": "기본급", "value": 2096900}]}  # 통상<기본 모순
    r = assess(e)
    by = {a["label"]: a["level"] for a in r["amounts"]}
    assert by["월 통상임금"] == "low" and by["기본급"] == "low"
    assert "월 통상임금" in r["review_fields"]


def test_교차일치_high():
    e = {"hourly_wage": 10030, "amounts": []}
    r = assess(e, cross={"hourly_wage": "agree"})
    assert r["fields"]["hourly_wage"]["level"] == "high"
    assert r["review_fields"] == []


def test_교차불일치_low():
    e = {"hourly_wage": 9000, "amounts": []}
    r = assess(e, cross={"hourly_wage": "disagree"})
    assert r["fields"]["hourly_wage"]["level"] == "low"
    assert "hourly_wage" in r["review_fields"]


def test_단일출처_medium():
    e = {"amounts": [{"label": "지급액", "value": 1800000}]}
    r = assess(e)
    assert r["amounts"][0]["level"] == "medium"
    assert r["review_fields"] == []


def test_누락필드는_없음():
    e = {"amounts": []}
    r = assess(e)
    assert r["fields"] == {} and r["amounts"] == []
