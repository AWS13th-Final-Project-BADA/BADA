"""원문-번역 대조표 조립 — 원문 항상 보존(병기). 번역만 translator에 위임.

대조표 항목: 면책 고지, 공제 항목, 미지급 의심 진술, 누락 자료 안내.
번역 호출 실패 시 원문 유지(폴백).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 면책 고지 원문 (product.md 4항 — 모든 산출물에 필수 노출)
DISCLAIMER_TEXT = (
    "본 자료는 법률자문이 아닌 상담 준비용 증거 정리 자료입니다. "
    "위법·체불 여부와 금액을 확정하지 않으며, "
    "최종 판단은 고용노동부 또는 전문기관에서 확인해야 합니다."
)


def _safe_translate(translator, source_text: str, target_lang: str) -> str:
    """Translate with graceful degradation: returns source_text on any failure.

    Ensures translated_text is never empty — falls back to source_text.
    """
    if not source_text:
        return source_text
    try:
        translated = translator.translate(source_text, target_lang)
        # Ensure non-empty: if translator returns empty, fall back to source
        if not translated:
            return source_text
        return translated
    except Exception as e:
        logger.warning(
            "Translation failed for target_lang=%s: %s. Using source text as fallback.",
            target_lang,
            str(e),
        )
        return source_text


def build_translation_pairs(ctx: dict, result: dict, translator, target_lang: str = "ko") -> list[dict]:
    """분석 결과에서 번역 대상을 추출하여 원문-번역 대조표를 생성한다.

    항목: 면책 고지(항상), 공제 설명, 미지급 의심 문구, 누락 자료 안내.
    모든 pair는 non-empty source_text, non-empty translated_text,
    evidence_type, related_issue를 가진다.
    """
    pairs: list[dict] = []

    # 1. 면책 고지 — 항상 포함 (Requirements 5.3)
    pairs.append({
        "source_text": DISCLAIMER_TEXT,
        "translated_text": _safe_translate(translator, DISCLAIMER_TEXT, target_lang),
        "evidence_type": "면책 고지",
        "related_issue": "disclaimer",
    })

    # 2. 공제 항목 (Requirements 5.1)
    for d in result.get("deduction_items", []):
        src = f"{d['name']} {int(d['amount']):,}원이 공제되었습니다. ({d['check']})"
        # 출처는 실제 자료(계약서/대화 등). 없으면 '공제'로만 표기(없는 문서유형을 지어내지 않음)
        srcs = d.get("sources") or []
        etype = "/".join(srcs) + "·공제" if srcs else "공제"
        pairs.append({
            "source_text": src,
            "translated_text": _safe_translate(translator, src, target_lang),
            "evidence_type": etype,
            "related_issue": "deduction",
        })

    # 3. 미지급 의심 금액 (Requirements 5.2)
    if result.get("suspected_unpaid") and result["suspected_unpaid"] > 0:
        src = f"급여와 입금액 사이에 약 {result['suspected_unpaid']:,}원의 차이가 확인됩니다. 확인이 필요합니다."
        pairs.append({
            "source_text": src,
            "translated_text": _safe_translate(translator, src, target_lang),
            "evidence_type": "사용자 진술",
            "related_issue": "wage_unpaid",
        })

    # 4. 누락 자료 안내 (missing_evidences)
    for item in result.get("missing_evidences", []):
        src = f"{item['item']}: {item['reason']}"
        pairs.append({
            "source_text": src,
            "translated_text": _safe_translate(translator, src, target_lang),
            "evidence_type": "누락 자료 안내",
            "related_issue": "missing_evidence",
        })

    return pairs
