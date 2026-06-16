"""공제 항목 분류 + 중복 제거 - 규칙 기반 사전 매핑(domain.md). LLM 사용 금지.

원문 표기의 변형을 정규화하고, 각 공제에 '계약서 명시 확인 필요' 플래그를 기본 부착한다.
여러 자료(계약서·카톡 등)에서 같은 공제가 다른 표기로 잡히면 한 건으로 합친다(중복 합산 방지).
"""
from __future__ import annotations

import re

# 정규화 사전: category -> 변형 표기들 (숙박/식사 부담금 등 동의어 포함)
DEDUCTION_LEXICON: dict[str, list[str]] = {
    "기숙사비": ["기숙사비", "숙소비", "기숙비", "방값", "숙박", "숙소", "기숙사", "dormitory", "dorm"],
    "식비": ["식비", "밥값", "식대", "식사", "meal", "food"],
    "작업복/장비": ["작업복비", "장비비", "유니폼", "안전화", "uniform", "equipment"],
    "보험/세금": ["국민연금", "건강보험", "장기요양", "고용보험", "소득세", "지방소득세",
                "보험료", "4대보험", "세금", "insurance", "tax"],
}

DEFAULT_CHECK = "계약서 명시 확인 필요"
_SRC_LABEL = {"contract": "계약서", "statement": "급여명세서", "chat": "대화", "payment": "입금내역", "other": "기타"}


def classify_name(raw: str) -> str:
    text = (raw or "").strip().lower()
    for category, variants in DEDUCTION_LEXICON.items():
        for v in variants:
            if v.lower() in text:
                return category
    return "기타공제"


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def classify_deductions(deductions: list[dict]) -> list[dict]:
    """deductions: [{"name": str, "amount": int, "source"?: str}, ...]

    분류 후 (category, amount)가 같으면 한 건으로 합친다(다른 표기·다른 출처 중복 제거).
    단 '기타공제'는 의미가 불명확하므로 이름까지 같을 때만 합친다(과합치기 방지).
    반환: [{"name", "category", "amount", "check", "sources"[]}]
    """
    seen: dict[tuple, dict] = {}
    out: list[dict] = []
    for d in deductions:
        category = classify_name(d.get("name", ""))
        amount = int(d.get("amount", 0))
        src = d.get("source")
        key = (category, amount) if category != "기타공제" else (category, amount, _norm(d.get("name", "")))
        if key in seen:
            if src and src not in seen[key]["_src"]:
                seen[key]["_src"].append(src)
            continue
        check = DEFAULT_CHECK if category != "기타공제" else "분류 불가 - 항목 성격과 계약 명시 여부 확인 필요"
        item = {"name": d.get("name", ""), "category": category, "amount": amount,
                "check": check, "_src": [src] if src else []}
        seen[key] = item
        out.append(item)

    # 출처 라벨 정리 + 여러 자료에서 확인된 경우 안내
    for item in out:
        srcs = [_SRC_LABEL.get(s, s) for s in item.pop("_src")]
        item["sources"] = srcs
        if len(srcs) >= 2:
            item["check"] += f" (여러 자료에서 확인: {', '.join(srcs)})"
    return out


def total_deductions(classified: list[dict]) -> int:
    return sum(item["amount"] for item in classified)
