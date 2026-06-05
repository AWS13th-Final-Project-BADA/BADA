"""분석 워커 — 단일 워커 순차(architecture.md). 규칙=계산·정렬·판정·대조, LLM=문장화만.

OCR 결과(엔티티·발화)를 받아 차액·공제·누락·GPS + 증거 대조(검증포인트) + 타임라인 + 요약을 만든다.
LLM/번역/OCR 실패해도 규칙 결과는 항상 반환(폴백). 요약은 가드레일로 법률 단정 표현 차단.
"""
from __future__ import annotations

from providers.llm import get_llm
from providers.ocr import get_ocr
from providers.translate import get_translator
from rules import compare as cmp
from rules import deductions as ded
from rules import geofence, guardrails, missing, wage
from services import timeline as tl
from services import translation as tr


def process_case(case_id: str, ctx: dict) -> dict:
    llm = get_llm()
    translator = get_translator()
    target_lang = ctx.get("target_lang", "ko")

    # 1단계: OCR (이미지 직접 전달 시). 보통은 /extract에서 미리 수행됨.
    for ev in ctx.get("evidences", []):
        if ev.get("image_bytes"):
            try:
                get_ocr(ev.get("category", "other")).extract(ev["image_bytes"], ev.get("category", "other"))
            except Exception:
                pass

    # 2단계: 규칙 기반 차액·공제·누락
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

    # 3단계: 증거 대조(검증포인트) — 계약↔명세서 시급, 명세서 실지급↔통장 입금
    result["compare"] = cmp.compare(ctx.get("evidence_entities", []))

    # 4단계: 번역 대조표
    result["translation_pairs"] = tr.build_translation_pairs(ctx, result, translator, target_lang)

    # 5단계: 타임라인 (규칙 정렬 + 카톡 발화 이벤트 + 문장화/번역)
    result["timeline"] = tl.build_timeline(ctx, result, llm, translator, target_lang)

    # 6단계: 요약 (LLM, 실패/빈값 시 폴백) → 가드레일로 단정 표현 차단
    descs = [e["description"] for e in result["timeline"]]
    try:
        summary = (llm.summarize_case(descs) or "").strip()
    except Exception:
        summary = ""
    if not summary:
        summary = " ".join(descs) or "업로드한 자료에서 분석할 정보를 확인하지 못했습니다. 자료를 더 올려주세요."
    result["timeline_summary"] = guardrails.sanitize(summary)

    return result
