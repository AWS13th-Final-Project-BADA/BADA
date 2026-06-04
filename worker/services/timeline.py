"""타임라인 조립 — 규칙 기반 정렬 + LLM 문장화 보조(architecture.md).

정렬·이벤트 선택은 규칙. 문장 다듬기는 llm.summarize_event, 번역 병기는 translator.
LLM/번역 호출이 실패해도(권한·네트워크 등) 규칙 결과는 살아있게 폴백한다.
"""
from __future__ import annotations


def _safe_summarize(llm, fact: str) -> str:
    try:
        return llm.summarize_event(fact)
    except Exception:
        return fact  # LLM 실패 시 사실 그대로


def _safe_translate(translator, text: str, lang: str) -> str:
    try:
        return translator.translate(text, lang)
    except Exception:
        return text  # 번역 실패 시 원문 유지


def build_timeline(ctx: dict, result: dict, llm, translator, target_lang: str = "ko") -> list[dict]:
    events: list[dict] = []
    wp = ctx.get("workplace_name") or "사업장"

    if ctx.get("work_start_date"):
        events.append({"date": str(ctx["work_start_date"]), "type": "work_start",
                       "fact": f"{ctx['work_start_date']}, {wp}에서 근무를 시작했습니다."})

    for dep in ctx.get("deposit_events", []):
        if dep.get("date"):
            events.append({"date": dep["date"], "type": "payment",
                           "fact": f"{dep['date']}, {int(dep['amount']):,}원이 입금되었습니다."})

    if result.get("suspected_unpaid") and result["suspected_unpaid"] > 0:
        events.append({"date": None, "type": "underpayment",
                       "fact": f"미지급 의심 금액 약 {result['suspected_unpaid']:,}원이 확인됩니다. (확정 아님, 확인 필요)"})

    gps = result.get("gps") or {}
    if gps.get("cross_matches"):
        events.append({"date": None, "type": "gps",
                       "fact": f"근무지 도착 정황(카톡-GPS 교차일치) {gps['cross_matches']}건이 확인됩니다."})

    events.sort(key=lambda e: (e["date"] is None, e["date"] or ""))

    out = []
    for e in events:
        desc = _safe_summarize(llm, e["fact"])
        out.append({
            "date": e["date"], "type": e["type"], "description": desc,
            "description_translated": _safe_translate(translator, desc, target_lang),
        })
    return out
