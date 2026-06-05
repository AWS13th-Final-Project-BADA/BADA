"""근거 기반 신뢰도(confidence) — LLM 자기보고 대신 '객관 신호'로 필드별 신뢰도를 매긴다.

왜? LLM이 스스로 붙이는 confidence는 보정이 안 돼서 과신 경향이 있다(틀려도 high).
대신 검증 가능한 신호로 다시 매긴다:
  - high   : 다른 증거와 교차 일치 (가장 강함 — 계약 시급 == 명세서 시급 등)
  - medium : 단일 출처에서 모순 없이 추출됨
  - low    : sanity 모순에 연루 / 증거 간 불일치 / (이 모듈은 누락은 다루지 않음)

이 신뢰도는 '확정'이 아니라 사용자가 어디를 먼저 확인·수정하면 좋은지(HITL) 안내용이다.
판단·계산은 하지 않는다(architecture.md).
"""
from __future__ import annotations

from rules.sanity import check_entities

# sanity가 짚은 field → 연루된 amount label 키워드 (low로 강등할 대상)
_SANITY_LABELS = {
    "통상임금/기본급": ("통상임금", "기본급"),
    "실지급액": ("실지급", "지급액 계", "지급액계", "지급총액", "지급 총액"),
    "명세서 산식": ("지급", "공제", "실지급"),
}

_SCALAR_FIELDS = ("hourly_wage", "monthly_wage", "pay_date", "workplace_name", "employer_name")


def _present(entities: dict, field: str) -> bool:
    v = entities.get(field)
    return v is not None and v != "" and v != []


def _flagged_label_keywords(sanity_flags: list[dict]) -> set[str]:
    kws: set[str] = set()
    for f in sanity_flags:
        kws.update(_SANITY_LABELS.get(f.get("field", ""), ()))
    return kws


def _grade(cross_result: str | None, in_sanity: bool) -> tuple[str, str]:
    if in_sanity:
        return "low", "값들이 서로 맞지 않습니다 — 확인이 필요해요."
    if cross_result == "disagree":
        return "low", "다른 증거와 숫자가 다릅니다 — 확인이 필요해요."
    if cross_result == "agree":
        return "high", "다른 증거와 일치합니다."
    return "medium", "단일 출처에서 추출 — 한 번 확인해 주세요."


def assess(entities: dict, cross: dict | None = None) -> dict:
    """단일 증거 엔티티 → 필드별 근거 confidence.

    cross: {key: 'agree'|'disagree'} 다른 증거와의 비교 결과(선택).
           key는 스칼라 필드명(hourly_wage 등) 또는 amount label.
    반환: {"fields": {name:{level,reason}}, "amounts": [{label,value,level,reason}],
           "review_fields": [낮은 신뢰로 확인이 필요한 필드/라벨...]}
    """
    cross = cross or {}
    flagged_kws = _flagged_label_keywords(check_entities(entities))

    fields: dict[str, dict] = {}
    for name in _SCALAR_FIELDS:
        if not _present(entities, name):
            continue
        lvl, reason = _grade(cross.get(name), in_sanity=False)
        fields[name] = {"level": lvl, "reason": reason}

    amounts: list[dict] = []
    for a in entities.get("amounts", []) or []:
        label = a.get("label") or "금액"
        in_sanity = any(kw in label for kw in flagged_kws)
        lvl, reason = _grade(cross.get(label), in_sanity=in_sanity)
        amounts.append({"label": label, "value": a.get("value"), "level": lvl, "reason": reason})

    review = [n for n, v in fields.items() if v["level"] == "low"]
    review += [a["label"] for a in amounts if a["level"] == "low"]

    return {"fields": fields, "amounts": amounts, "review_fields": review}
