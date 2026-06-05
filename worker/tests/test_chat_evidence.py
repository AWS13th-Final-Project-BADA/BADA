"""카톡 증거력 평가 테스트."""
from rules.chat_evidence import assess_chat


def test_strong_capture():
    en = {
        "dates": ["2026-05-02"],
        "amounts": [{"label": "급여", "value": 400000}],
        "utterances": [
            {"speaker": "사업주", "text": "이번 주 금요일까지 40만원 줄게", "kind": "wage_promise"},
            {"speaker": "근로자", "text": "네 기다릴게요", "kind": "other"},
            {"speaker": "사업주", "text": "지난달 급여는 아직 못 줬어 미안", "kind": "underpayment_admit"},
        ],
    }
    r = assess_chat(en)
    assert r["score"] == 5 and r["level"] == "high"
    assert r["warnings"] == []
    assert len(r["key_statements"]) == 2


def test_weak_capture():
    en = {"dates": [], "amounts": [], "utterances": [
        {"speaker": "?", "text": "ㅇㅇ", "kind": "other"}]}
    r = assess_chat(en)
    assert r["level"] == "low"
    assert any("상대 식별" in w for w in r["warnings"])
    assert any("날짜" in w for w in r["warnings"])
    assert any("맥락" in w for w in r["warnings"])


def test_medium_capture():
    en = {"dates": ["2026-05-02"], "amounts": [],
          "utterances": [{"speaker": "사업주", "text": "다음 주 지급", "kind": "wage_promise"}]}
    r = assess_chat(en)
    # 상대식별 + 날짜 + 핵심문장 = 3 → high? 3 items true → score 3 → medium
    assert r["level"] in ("medium", "high")
    assert r["checklist"]["지급약속/체불인정 문장"] is True
