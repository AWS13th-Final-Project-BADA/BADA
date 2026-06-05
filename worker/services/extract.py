"""증거별 OCR 엔티티 → 분석 입력으로 집계(규칙 기반, 생성형 X).

여러 문서에서 뽑힌 엔티티를 worked_hours/deposits/deductions/시급 등으로 모은다.
집계는 '추정'이므로 결과는 사용자 검토(HITL) 후 확정한다.
값이 None(못 읽음)인 항목은 건너뛴다.
"""
from __future__ import annotations

_DEPOSIT_HINTS = ("입금", "실지급", "실수령", "deposit")


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def aggregate(evidences: list[dict]) -> dict:
    """evidences: [{"category": str, "entities": {...}}]. 반환: 분석 입력 추정값 + confidence 표시."""
    hours: list[float] = []
    deposits: list[dict] = []
    deductions: list[dict] = []
    hourly_wage = None
    workplace_name = None
    employer_name = None
    low_conf = False

    for ev in evidences:
        e = ev.get("entities") or {}
        cat = ev.get("category")

        for h in e.get("hours", []) or []:
            f = None
            try:
                f = float(h)
            except (TypeError, ValueError):
                f = None
            if f is not None:
                hours.append(f)

        if e.get("hourly_wage") and not hourly_wage:
            hourly_wage = _int(e["hourly_wage"])
        workplace_name = workplace_name or e.get("workplace_name")
        employer_name = employer_name or e.get("employer_name")

        for d in e.get("deductions", []) or []:
            amt = _int(d.get("amount"))
            if amt is None:
                continue
            # source(증거 카테고리) 보존 — 중복 제거·출처 라벨링에 사용
            deductions.append({"name": d.get("name") or "공제", "amount": amt, "source": cat})
            if d.get("confidence") == "low":
                low_conf = True

        for a in e.get("amounts", []) or []:
            amt = _int(a.get("value"))
            if amt is None:
                continue
            label = a.get("label") or ""
            if cat == "payment" or any(h in label for h in _DEPOSIT_HINTS):
                deposits.append({"date": e.get("pay_date"), "amount": amt})
            if a.get("confidence") == "low":
                low_conf = True

    return {
        "worked_hours": hours,
        "deposits": deposits,
        "deductions": deductions,
        "agreed_hourly_wage": hourly_wage,
        "workplace_name": workplace_name,
        "employer_name": employer_name,
        "needs_review": low_conf or not hours or not deposits,
    }
