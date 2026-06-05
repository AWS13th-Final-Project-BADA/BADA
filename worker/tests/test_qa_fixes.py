"""QA 지적사항 수정 검증 — 중복제거·숫자환각가드·빈입금·법령연도·오타."""
from rules import guardrails, legal
from rules.deductions import classify_deductions
from rules.wage import compute_unpaid


# B. 공제 중복 제거 (다른 표기·다른 출처, 같은 금액)
def test_공제_중복제거():
    items = classify_deductions([
        {"name": "숙박시설 부담금", "amount": 250000, "source": "contract"},
        {"name": "식사 부담금", "amount": 150000, "source": "contract"},
        {"name": "기숙사비", "amount": 250000, "source": "chat"},
        {"name": "식비", "amount": 150000, "source": "chat"},
    ])
    # 4개가 2개(기숙사비/식비)로 합쳐져야 한다
    cats = sorted(i["category"] for i in items)
    assert cats == ["기숙사비", "식비"]
    total = sum(i["amount"] for i in items)
    assert total == 400000  # 800000 아님
    dorm = next(i for i in items if i["category"] == "기숙사비")
    assert set(dorm["sources"]) == {"계약서", "대화"}


# A. LLM 숫자 환각 가드
def test_숫자환각_탐지():
    assert guardrails.has_foreign_number("실제 9,030원이 입금", "통장에 9,000원이 입금") is True
    assert guardrails.has_foreign_number("9,000원이 입금", "통장에 9,000원 입금됨") is False


def test_keep_grounded_되돌림():
    src = "2026-01-12, 9,000원이 입금되었습니다."
    bad = "2026-01-12, 9,030원이 입금되었습니다."
    assert guardrails.keep_grounded(bad, src) == src   # 환각 → 원문 복귀
    good = "9,000원이 입금됨"
    assert guardrails.keep_grounded(good, src) == good  # 정상 → 유지


# 보너스. OCR 오타 보정
def test_오타보정():
    assert "야근수당" in guardrails.sanitize("아근수당 미지급 의심")


# C. 입금 자료 없으면 0원 단정 금지
def test_빈입금_확인불가():
    r = compute_unpaid(10030, [174.0], [])
    assert r.total_received_wage is None     # 0 아님
    assert r.suspected_unpaid is None
    assert r.total_expected_wage == int(round(10030 * 174))


# E1. 법령 연도 추정 + 실효 지급률
def test_법령_연도추정():
    assert legal.infer_year({"work_start_date": "2025-11-01"}) == 2025
    assert legal.infer_year({"evidence_entities": [{"entities": {"pay_date": "2025-12-10"}}]}) == 2025


def test_2025년_계약시급_10030은_위반아님():
    ctx = {"agreed_hourly_wage": 10030, "work_start_date": "2025-11-01", "worked_hours": [174.0]}
    r = legal.legal_review(ctx, {"calculation_detail": {"hours_sum": 174.0}})
    assert r["min_wage_year"] == 2025
    assert not any(f["type"] == "minimum_wage" for f in r["findings"])  # 10030 == 2025 최저


def test_실지급_시급_최저미달_탐지():
    ctx = {"agreed_hourly_wage": 10030, "work_start_date": "2025-11-01", "worked_hours": [174.0]}
    # 실제 지급 174h에 1,566,000 → 시급 9,000 < 10,030
    result = {"calculation_detail": {"hours_sum": 174.0}, "total_received_wage": 9000 * 174}
    r = legal.legal_review(ctx, result)
    assert any(f["type"] == "minimum_wage_paid" for f in r["findings"])
