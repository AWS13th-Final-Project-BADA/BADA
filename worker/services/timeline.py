"""타임라인 조립 — 규칙 기반 정렬 + LLM 문장화 보조(architecture.md).

정렬·이벤트 선택은 규칙. 문장 다듬기는 llm.summarize_event(mock=항등).
번역 병기는 translator.translate_batch()로 효율적 배치 번역.
원문(description)은 절대 수정하지 않는다 (원문 보존 원칙).
"""
from __future__ import annotations


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

    # 규칙 정렬: 날짜 있는 것 오름차순, 없는 것 뒤로
    events.sort(key=lambda e: (e["date"] is None, e["date"] or ""))

    # LLM 문장화: 각 fact를 description으로 변환 (mock=항등)
    descriptions: list[str] = []
    for e in events:
        desc = llm.summarize_event(e["fact"])
        descriptions.append(desc)

    # 배치 번역: translate_batch로 한 번에 번역 (효율적, 순서·길이 보존)
    # translate_batch는 target_lang=="ko"이면 입력 그대로 반환하고,
    # 개별 항목 실패 시 해당 항목은 원문 반환 (graceful degradation).
    translated_descriptions = translator.translate_batch(descriptions, target_lang)

    # 결과 조립: description(원문)은 절대 수정하지 않음
    out = []
    for i, e in enumerate(events):
        out.append({
            "date": e["date"],
            "type": e["type"],
            "description": descriptions[i],
            "description_translated": translated_descriptions[i],
        })
    return out
