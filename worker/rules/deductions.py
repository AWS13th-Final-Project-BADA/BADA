"""공제 항목 분류 - 규칙 기반 사전 매핑(domain.md). LLM 사용 금지.

원문 표기의 변형을 정규화하고, 각 공제에 '계약서 명시 확인 필요' 플래그를 기본 부착한다.
"""
from __future__ import annotations

# 정규화 사전: category -> 변형 표기들
DEDUCTION_LEXICON: dict[str, list[str]] = {
    "기숙사비": ["기숙사비", "숙소비", "기숙비", "방값", "dormitory", "dorm"],
    "식비": ["식비", "밥값", "meal", "food"],
    "작업복/장비": ["작업복비", "장비비", "유니폼", "안전화", "uniform", "equipment"],
    "보험/세금": ["보험료", "4대보험", "소득세", "세금", "insurance", "tax"],
}

DEFAULT_CHECK = "계약서 명시 확인 필요"


def classify_name(raw: str) -> str:
    text = (raw or "").strip().lower()
    for category, variants in DEDUCTION_LEXICON.items():
        for v in variants:
            if v.lower() in text:
                return category
    return "기타공제"


def classify_deductions(deductions: list[dict]) -> list[dict]:
    """deductions: [{"name": str, "amount": int}, ...]
    반환: [{"name": 원문, "category": 정규화, "amount": int, "check": 안내문}]
    """
    out: list[dict] = []
    for d in deductions:
        category = classify_name(d.get("name", ""))
        check = DEFAULT_CHECK
        if category == "기타공제":
            check = "분류 불가 - 항목 성격과 계약 명시 여부 확인 필요"
        out.append({
            "name": d.get("name", ""),
            "category": category,
            "amount": int(d.get("amount", 0)),
            "check": check,
        })
    return out


def total_deductions(classified: list[dict]) -> int:
    return sum(item["amount"] for item in classified)
