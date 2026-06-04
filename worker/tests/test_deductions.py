from rules.deductions import classify_deductions, classify_name, total_deductions


def test_lexicon_normalization():
    assert classify_name("기숙사비") == "기숙사비"
    assert classify_name("숙소비 공제") == "기숙사비"
    assert classify_name("방값") == "기숙사비"
    assert classify_name("밥값") == "식비"
    assert classify_name("안전화 구입") == "작업복/장비"
    assert classify_name("정체불명 항목") == "기타공제"


def test_classify_attaches_check_flag():
    items = classify_deductions([
        {"name": "기숙사비", "amount": 250_000},
        {"name": "이상한공제", "amount": 50_000},
    ])
    assert items[0]["category"] == "기숙사비"
    assert items[0]["check"]  # 확인 필요 플래그 존재
    assert items[1]["category"] == "기타공제"
    assert "분류 불가" in items[1]["check"]
    assert total_deductions(items) == 300_000
