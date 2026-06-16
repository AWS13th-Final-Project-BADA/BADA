"""증거 간 대조(검증 포인트) — 규칙 기반. 생성형 X.

여러 문서의 추출 엔티티를 받아 '비교 키'를 산출한다(ProofPack 핵심 가치).
- 계약 시급 ↔ 명세서 시급
- 명세서 실지급액 ↔ 통장 입금액 합
결과는 '확정' 아님 — match/mismatch/missing + '확인 필요' 표기(product.md).
"""
from __future__ import annotations


def _find_amount(entities: dict, *hints: str):
    """amounts[] 에서 label에 hint가 포함된 값을 찾는다."""
    for a in entities.get("amounts", []) or []:
        label = a.get("label") or ""
        if any(h in label for h in hints):
            try:
                return int(a.get("value"))
            except (TypeError, ValueError):
                pass
    return None


def _by_category(evidences: list[dict]) -> dict:
    by: dict[str, list[dict]] = {}
    for ev in evidences:
        by.setdefault(ev.get("category"), []).append(ev.get("entities") or {})
    return by


def _first(by: dict, cat: str, key: str):
    for e in by.get(cat, []):
        if e.get(key):
            return e[key]
    return None


def compare(evidences: list[dict]) -> list[dict]:
    """evidences: [{"category": str, "entities": {...}}]. 반환: 검증 포인트 리스트."""
    by = _by_category(evidences)
    points: list[dict] = []

    # 1) 계약 시급 ↔ 명세서 시급
    c_wage = _first(by, "contract", "hourly_wage")
    s_wage = _first(by, "statement", "hourly_wage")
    if s_wage is None:
        for e in by.get("statement", []):
            s_wage = _find_amount(e, "시급")
            if s_wage:
                break
    if c_wage and s_wage:
        points.append({
            "key": "hourly_wage", "label": "계약 시급 vs 명세서 시급",
            "values": {"계약": int(c_wage), "명세서": int(s_wage)},
            "status": "match" if int(c_wage) == int(s_wage) else "mismatch",
            "note": "" if int(c_wage) == int(s_wage) else "시급이 다릅니다. 확인이 필요합니다.",
        })
    elif c_wage or s_wage:
        points.append({
            "key": "hourly_wage", "label": "계약 시급 vs 명세서 시급",
            "values": {"계약": c_wage, "명세서": s_wage},
            "status": "missing", "note": "한쪽 자료가 없어 비교할 수 없습니다.",
        })

    # 2) 명세서 실지급액 ↔ 통장 입금액 합
    net = None
    for e in by.get("statement", []):
        net = _find_amount(e, "실지급", "실수령") or net
    deposits = 0
    has_pay = False
    for e in by.get("payment", []):
        for a in e.get("amounts", []) or []:
            try:
                deposits += int(a.get("value", 0))
                has_pay = True
            except (TypeError, ValueError):
                pass
    if net and has_pay:
        diff = int(net) - deposits
        points.append({
            "key": "net_vs_deposit", "label": "명세서 실지급액 vs 통장 입금액",
            "values": {"명세서": int(net), "통장": deposits, "차액": diff},
            "status": "match" if diff == 0 else "mismatch",
            "note": "" if diff == 0 else f"약 {abs(diff):,}원 차이가 확인됩니다. 확인이 필요합니다.",
        })
    elif net or has_pay:
        points.append({
            "key": "net_vs_deposit", "label": "명세서 실지급액 vs 통장 입금액",
            "values": {"명세서": net, "통장": deposits if has_pay else None},
            "status": "missing", "note": "한쪽 자료가 없어 비교할 수 없습니다.",
        })

    return points
