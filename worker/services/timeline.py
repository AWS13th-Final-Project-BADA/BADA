"""타임라인 조립 — 규칙 정렬 + LLM 문장화 보조 + 카톡 발화 이벤트화(architecture.md).

정렬·이벤트 선택은 규칙. 문장 다듬기는 llm.summarize_event(mock=항등) + 숫자 환각 가드.
번역 병기는 translator.translate_batch()로 효율적 배치 번역(실패 시 원문).
카톡 발화는 '확정'이 아니라 중립 표현 + 원문 병기 + 출처 + confidence=low(확인 필요).
원문(description)은 절대 수정하지 않는다 (원문 보존 원칙).
"""
from __future__ import annotations

_UTT_LABEL = {
    "wage_promise": "급여 지급을 언급함",
    "underpayment_admit": "미지급/지연을 언급함",
    "work_order": "근무를 지시함",
}


def _ss(llm, fact, lang="ko"):
    try:
        return llm.summarize_event(fact, lang=lang)
    except Exception:
        return fact


def _st(translator, text, lang):
    try:
        return translator.translate(text, lang)
    except Exception:
        return text


def build_timeline(ctx: dict, result: dict, llm, translator, target_lang: str = "ko") -> list[dict]:
    raw: list[dict] = []
    wp = ctx.get("workplace_name") or "사업장"

    if ctx.get("work_start_date"):
        raw.append({"date": str(ctx["work_start_date"]), "type": "work_start", "confidence": "high",
                    "source": None, "fact": f"{ctx['work_start_date']}, {wp}에서 근무를 시작했습니다."})

    for dep in ctx.get("deposit_events", []):
        if dep.get("date"):
            raw.append({"date": dep["date"], "type": "payment", "confidence": "medium", "source": None,
                        "fact": f"{dep['date']}, {int(dep['amount']):,}원이 입금되었습니다."})

    # 카톡 발화 → 이벤트 (중립 표현 + 원문 병기, 확인 필요)
    for u in ctx.get("chat_utterances", []):
        kind = u.get("kind")
        if kind not in _UTT_LABEL:
            continue
        speaker = u.get("speaker") or "상대방"
        text = (u.get("text") or "").strip()
        label = _UTT_LABEL[kind]
        fact = f'{speaker}가 {label}: "{text}"' if text else f"{speaker}가 {label}."
        raw.append({"date": u.get("date"), "type": "chat", "confidence": "low",
                    "source": u.get("source_evidence_id"), "fact": fact})

    if result.get("suspected_unpaid") and result["suspected_unpaid"] > 0:
        raw.append({"date": None, "type": "underpayment", "confidence": "medium", "source": None,
                    "fact": f"미지급 의심 금액 약 {result['suspected_unpaid']:,}원이 확인됩니다. (확정 아님, 확인 필요)"})

    gps = result.get("gps") or {}
    if gps.get("cross_matches"):
        raw.append({"date": None, "type": "gps", "confidence": "medium", "source": None,
                    "fact": f"근무지 도착 정황(카톡-GPS 교차일치) {gps['cross_matches']}건이 확인됩니다."})

    raw.sort(key=lambda e: (e["date"] is None, e["date"] or ""))

    from rules import guardrails  # worker

    # LLM 문장화 + 숫자 환각 가드(없는 금액 생성 시 결정론적 원문 복귀)
    descriptions: list[str] = []
    for e in raw:
        desc = _ss(llm, e["fact"], target_lang)
        descriptions.append(guardrails.keep_grounded(desc, e["fact"]))

    # 배치 번역(효율적, 순서·길이 보존, ko면 원문 그대로). 실패 시 원문 폴백.
    try:
        translated = translator.translate_batch(descriptions, target_lang)
    except Exception:
        translated = list(descriptions)

    # description(원문)은 절대 수정하지 않음 + 출처·confidence 부착
    out = []
    for i, e in enumerate(raw):
        out.append({
            "date": e["date"], "type": e["type"], "description": descriptions[i],
            "description_translated": translated[i] if i < len(translated) else descriptions[i],
            "source_evidence_id": e["source"], "confidence": e["confidence"],
        })
    return out
