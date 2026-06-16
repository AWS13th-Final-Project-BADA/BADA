from rules.category_keywords import (
    best_keyword_category,
    keyword_score,
    verify_category,
)


def test_keyword_score_counts_matches():
    text = "근로계약서 갑 을 서명 근로조건"
    assert keyword_score("contract", text) >= 4
    assert keyword_score("payment", text) == 0


def test_best_category_picks_dominant():
    text = "급여명세서 기본급 수당 공제 실수령액 지급총액"
    cat, score = best_keyword_category(text)
    assert cat == "statement"
    assert score >= 4


def test_best_category_empty_text():
    assert best_keyword_category("") == (None, 0)


def test_verify_agree_when_content_matches():
    # 형태=contract, 내용도 계약서 단어 → 일치
    res = verify_category("contract", "근로계약서 갑 을 서명 근로조건 계약기간")
    assert res["agree"] is True
    assert res["conflict"] is False
    assert res["category_score"] >= 3


def test_verify_conflict_when_content_differs():
    # 형태=contract 라고 했지만 내용은 급여명세서 강한 신호 → 충돌
    res = verify_category("contract", "급여명세서 지급총액 공제총액 실수령 기본급 수당")
    assert res["conflict"] is True
    assert res["agree"] is False


def test_verify_no_text_holds_judgement():
    # OCR 텍스트 없음(대화캡처 등) → 대조 보류, agree=False지만 conflict 아님
    res = verify_category("chat", "")
    assert res["agree"] is False
    assert res["conflict"] is False
