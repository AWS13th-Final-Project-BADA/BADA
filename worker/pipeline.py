"""분석 워커 — 단일 워커 순차 8단계(architecture.md). Step Functions 미사용.

설계 원칙: 계산·정렬·판정은 규칙엔진(rules/), 문장화·OCR·번역만 provider(providers/).
LLM/번역/OCR 호출이 실패해도 규칙 기반 결과는 항상 반환된다(폴백).
"""
from __future__ import annotations

from providers.llm import get_llm
from providers.ocr import get_ocr
from providers.translate import get_translator
from rules import deductions as ded
from rules import geofence, missing, wage
from services import timeline as tl
from services import translation as tr


def process_case(case_id: str, ctx: dict) -> dict:
    llm = get_llm()
    translator = get_translator()
    target_lang = ctx.get("target_lang", "ko")

    # 1단계: OCR (provider). 로컬 mock은 빈 결과. (이미지 추출은 /extract 에서도 수행)
    for ev in ctx.get("evidences", []):
        if ev.get("image_bytes"):
            try:
                get_ocr(ev.get("category", "other")).extract(ev["image_bytes"], ev.get("category", "other"))
            except Exception:
                pass  # OCR 실패는 규칙 분석을 막지 않음

    # 2단계: 규칙 기반 차액·공제 (생성형 X)
    w = wage.compute_unpaid(ctx.get("agreed_hourly_wage"), ctx.get("worked_hours", []), ctx.get("deposits", []))
    classified = ded.classify_deductions(ctx.get("raw_deductions", []))
    miss = missing.check_missing(set(ctx.get("present_categories", [])))

    gps_result: dict = {}
    wp = ctx.get("workplace")
    if wp and ctx.get("gps_logs"):
        tagged = geofence.tag_logs(ctx["gps_logs"], wp["lat"], wp["lng"], wp.get("radius_m", 50))
        matches = geofence.cross_check(tagged, ctx.get("chat_arrivals", []))
        gps_result = {"tagged_count": len(tagged), "cross_matches": len(matches)}

    result = {
        "total_expected_wage": w.total_expected_wage,
        "total_received_wage": w.total_received_wage,
        "suspected_unpaid": w.suspected_unpaid,
        "calculation_detail": w.calculation_detail,
        "deduction_items": classified,
        "deduction_total": ded.total_deductions(classified),
        "missing_evidences": miss,
        "gps": gps_result,
        "notes": w.notes,
    }

    # 3단계: 번역 + 대조표 (실패 시 원문 유지)
    result["translation_pairs"] = tr.build_translation_pairs(ctx, result, translator, target_lang)

    # 4단계: 타임라인 = 규칙 정렬 + LLM 문장화 + 번역 (실패 시 사실 그대로)
    result["timeline"] = tl.build_timeline(ctx, result, llm, translator, target_lang)

    # 7단계 요약: LLM (실패 시 사실 결합으로 폴백)
    try:
        result["timeline_summary"] = llm.summarize_case([e["description"] for e in result["timeline"]])
    except Exception:
        result["timeline_summary"] = " ".join(e["description"] for e in result["timeline"])

    return result
