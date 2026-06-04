"""원문-번역 대조표 조립 — 원문 항상 보존(병기). 번역만 translator에 위임.

번역 호출 실패 시 원문 유지(폴백). 대조표 항목: 공제·미지급 의심 진술 등.
"""
from __future__ import annotations


def _safe_translate(translator, text: str, lang: str) -> str:
    try:
        return translator.translate(text, lang)
    except Exception:
        return text


def build_translation_pairs(ctx: dict, result: dict, translator, target_lang: str = "ko") -> list[dict]:
    pairs: list[dict] = []

    for d in result.get("deduction_items", []):
        src = f"{d['name']} {int(d['amount']):,}원이 공제되었습니다. ({d['check']})"
        pairs.append({
            "source_text": src,
            "translated_text": _safe_translate(translator, src, target_lang),
            "evidence_type": "급여명세서/공제",
            "related_issue": "deduction",
        })

    if result.get("suspected_unpaid") and result["suspected_unpaid"] > 0:
        src = f"급여와 입금액 사이에 약 {result['suspected_unpaid']:,}원의 차이가 확인됩니다. 확인이 필요합니다."
        pairs.append({
            "source_text": src,
            "translated_text": _safe_translate(translator, src, target_lang),
            "evidence_type": "사용자 진술",
            "related_issue": "wage_unpaid",
        })

    return pairs
