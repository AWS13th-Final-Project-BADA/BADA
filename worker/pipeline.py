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
from rules import geofence, guardrails, legal, missing, wage
from services import timeline as tl
from services import translation as tr


def process_case(case_id: str, ctx: dict) -> dict:
    """ctx 입력으로 분석 결과 dict 반환. (OCR이 채워졌다고 가정한 구조화 값 사용)

    ctx 키: agreed_hourly_wage, worked_hours[], deposits[](int 합산용),
            deposit_events[{date,amount}], raw_deductions[{name,amount}],
            present_categories(set), gps_logs[{ts,lat,lng,is_mocked,is_delayed_upload}],
            workplace{lat,lng,radius_m}, chat_arrivals[datetime],
            work_start_date, workplace_name, target_lang,
            evidences[{image_bytes,category}] (선택, OCR용)

    gps_logs의 is_delayed_upload=True 핑은 geofence.tag_logs()에서 자동 배제된다.
    """
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
        results = geofence.cross_check(tagged, ctx.get("chat_arrivals", []))
        # 버그#6 수정 반영: cross_check는 match=False도 반환하므로 match=True만 카운트
        gps_result = {
            "tagged_count": len(tagged),
            "excluded_count": sum(1 for t in tagged if t.get("excluded")),
            "in_count": sum(1 for t in tagged if t.get("status") == "IN_WORKPLACE"),
            "out_count": sum(1 for t in tagged if t.get("status") == "OUTSIDE"),
            "cross_matches": sum(1 for r in results if r["match"]),
            "cross_mismatches": sum(1 for r in results if not r["match"]),
            "daily": geofence.summarize_by_day(tagged),
        }

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

    # 3-1단계: 법정 기준 점검 — 최저임금 미달·가산수당 추정·과다공제(법령 산식 매핑)
    result["legal"] = legal.legal_review(ctx, result)

    # 4단계: 번역 대조표
    result["translation_pairs"] = tr.build_translation_pairs(ctx, result, translator, target_lang)

    # 5단계: 타임라인 (규칙 정렬 + 카톡 발화 이벤트 + 문장화/번역)
    result["timeline"] = tl.build_timeline(ctx, result, llm, translator, target_lang)

    # 6단계: 요약 (LLM, 실패/빈값 시 폴백) → 가드레일로 단정 표현 차단
    descs = [e["description"] for e in result["timeline"]]
    src = " ".join(descs)
    try:
        summary = (llm.summarize_case(descs, lang=target_lang) or "").strip()
    except Exception:
        summary = ""
    # 숫자 환각 가드: 요약이 사실 목록에 없는 금액을 단정하면 결정론적 사실로 되돌림
    if not summary or guardrails.has_foreign_number(summary, src):
        summary = src or "업로드한 자료에서 분석할 정보를 확인하지 못했습니다. 자료를 더 올려주세요."
    result["timeline_summary"] = guardrails.sanitize(summary)

    return result
