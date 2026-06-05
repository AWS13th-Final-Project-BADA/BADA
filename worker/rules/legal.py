"""법령 산식 매핑 — 한국 노동법의 '명백한 기준'을 상수·공식으로 박아 둔다(규칙 기반, LLM X).

목적: sanity가 '숫자끼리 안 맞나'(내부 정합성)를 본다면, 여기서는
'법정 기준에 미달하나'(외부 기준)를 본다. 근거(산식)를 함께 남겨 상담사가 검증할 수 있게 한다.

원칙(security/product.md):
  - 명백히 법으로 정해진 것만 자신있게 계산한다(최저임금 등).
  - 통상임금 산정처럼 예외가 많은 영역은 억지로 판정하지 않고 '전문가 확인'으로 둔다.
  - 모든 결과는 '확정'이 아니라 '확인 필요' 안내.

상수는 매년 바뀌므로 연도별 dict로 두고 갱신한다.
"""
from __future__ import annotations

# 법정 최저시급(원) — 연도별. 매년 고시되면 추가/갱신.
MIN_HOURLY_WAGE: dict[int, int] = {2024: 9860, 2025: 10030, 2026: 10320}
LATEST_YEAR = 2026

# 월 소정근로시간(주 40h + 주휴 환산). 월급↔시급 환산 기준.
MONTHLY_STD_HOURS = 209

# 가산 배율(근로기준법). 연장/휴일은 통상의 1.5배, 야간은 +0.5배 가산.
OVERTIME_MULT = 1.5
NIGHT_EXTRA = 0.5
HOLIDAY_MULT = 1.5

# 4대보험 근로자 부담 '대략' 요율 — 과다공제 의심 판단 기준(연도별 변동, 보수적으로만 사용).
INSURANCE_RATES: dict[str, float] = {
    "국민연금": 0.045,
    "건강보험": 0.03545,
    "장기요양": 0.03545 * 0.1295,   # 건강보험료의 12.95%
    "고용보험": 0.009,
}
_INSURANCE_KEYS = {
    "국민연금": ("국민연금", "연금"),
    "건강보험": ("건강보험",),
    "장기요양": ("장기요양", "요양"),
    "고용보험": ("고용보험",),
}


def min_hourly_wage(year: int | None = None) -> int:
    return MIN_HOURLY_WAGE.get(year or LATEST_YEAR, MIN_HOURLY_WAGE[LATEST_YEAR])


def check_minimum_wage(hourly_wage: int | None, hours_sum: float | None = None,
                       year: int | None = None) -> dict | None:
    """약속/실효 시급이 법정 최저임금 미만인지. 미달 시 부족액 산식과 함께 반환."""
    if not hourly_wage:
        return None
    y = year or LATEST_YEAR
    floor = min_hourly_wage(y)
    if hourly_wage >= floor:
        return None
    per_hour = floor - hourly_wage
    f = {
        "type": "minimum_wage", "level": "high",
        "note": f"시급 {hourly_wage:,}원이 {y}년 법정 최저임금 {floor:,}원보다 {per_hour:,}원 낮습니다 — 확인이 필요해요.",
        "shortfall_per_hour": per_hour, "min_wage": floor, "year": y,
    }
    if hours_sum:
        f["shortfall_total"] = int(round(per_hour * hours_sum))
        f["note"] += f" (확인된 {hours_sum:g}시간 기준 약 {f['shortfall_total']:,}원)"
    return f


def expected_premium_pay(hourly_wage: int | None, overtime_h: float = 0,
                         night_h: float = 0, holiday_h: float = 0) -> dict | None:
    """연장·야간·휴일 '가산분'(기본급 외 추가로 받아야 할 부분) 추정.

    이중계산 방지를 위해 가산분(연장 0.5 / 야간 0.5 / 휴일 0.5)만 추정한다.
    이는 '추정'이며 통상임금 산정에 따라 달라질 수 있어 '확인 필요'로만 안내한다.
    """
    if not hourly_wage:
        return None
    ot = (overtime_h or 0) * 0.5
    ni = (night_h or 0) * 0.5
    ho = (holiday_h or 0) * 0.5
    units = ot + ni + ho
    if units <= 0:
        return None
    amount = int(round(hourly_wage * units))
    parts = []
    if overtime_h:
        parts.append(f"연장 {overtime_h:g}h")
    if night_h:
        parts.append(f"야간 {night_h:g}h")
    if holiday_h:
        parts.append(f"휴일 {holiday_h:g}h")
    return {
        "type": "premium_pay", "level": "medium",
        "note": f"{', '.join(parts)}에 대한 가산수당(추정 약 {amount:,}원)이 지급됐는지 확인이 필요해요. "
                "통상임금 산정에 따라 달라질 수 있어 정확한 금액은 전문가 확인이 필요합니다.",
        "estimated_premium": amount,
    }


def _classify_insurance(name: str) -> str | None:
    n = (name or "")
    for key, kws in _INSURANCE_KEYS.items():
        if any(k in n for k in kws):
            return key
    return None


def check_insurance_over_deduction(deductions: list[dict], base_wage: int | None) -> list[dict]:
    """4대보험 공제가 표준 요율 대비 과도한지(보수적: 기대치의 1.5배 초과만 플래그)."""
    if not base_wage:
        return []
    out: list[dict] = []
    for d in deductions or []:
        key = _classify_insurance(d.get("name", ""))
        if not key:
            continue
        amt = d.get("amount")
        if not amt:
            continue
        expected = base_wage * INSURANCE_RATES[key]
        if expected > 0 and amt > expected * 1.5:
            out.append({
                "type": "insurance_over", "level": "medium",
                "note": f"{d.get('name')} 공제 {int(amt):,}원이 표준 요율 추정({int(round(expected)):,}원)보다 많습니다 — 확인이 필요해요.",
                "deduction": d.get("name"), "expected": int(round(expected)), "actual": int(amt),
            })
    return out


def _agg_hours(evidence_entities: list[dict], field: str) -> float:
    total = 0.0
    for ev in evidence_entities or []:
        v = (ev.get("entities") or {}).get(field)
        if isinstance(v, (int, float)):
            total += v
    return total


def _first_monthly_wage(evidence_entities: list[dict]) -> int | None:
    for ev in evidence_entities or []:
        v = (ev.get("entities") or {}).get("monthly_wage")
        if v:
            return v
    return None


def legal_review(ctx: dict, result: dict | None = None) -> dict:
    """ctx(분석 입력) + result(차액 등)에서 법정 기준 점검 결과를 모은다.

    반환: {"findings": [...], "min_wage_year": int, "min_wage": int}
    findings 각 항목: {type, level, note, (+산식 근거 필드)}
    """
    result = result or {}
    findings: list[dict] = []

    hourly = ctx.get("agreed_hourly_wage")
    hours_sum = (result.get("calculation_detail") or {}).get("hours_sum") or sum(ctx.get("worked_hours", []) or [])

    mw = check_minimum_wage(hourly, hours_sum)
    if mw:
        findings.append(mw)

    ents = ctx.get("evidence_entities", [])
    prem = expected_premium_pay(
        hourly,
        _agg_hours(ents, "overtime_hours"),
        _agg_hours(ents, "night_hours"),
        _agg_hours(ents, "holiday_hours"),
    )
    if prem:
        findings.append(prem)

    base = _first_monthly_wage(ents) or (hourly * MONTHLY_STD_HOURS if hourly else None)
    findings.extend(check_insurance_over_deduction(ctx.get("raw_deductions", []), base))

    return {"findings": findings, "min_wage_year": LATEST_YEAR, "min_wage": min_hourly_wage()}
