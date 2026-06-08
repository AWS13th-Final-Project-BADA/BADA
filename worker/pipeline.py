"""분석 워커 — 단일 워커 순차 8단계(architecture.md). Step Functions 미사용.

설계 원칙: 계산·정렬·판정은 규칙엔진(rules/), 문장화·OCR·번역만 provider(providers/).
PROVIDER_MODE=local 이면 Mock으로 전 단계가 동작한다.
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
    """ctx 입력으로 분석 결과 dict 반환. (OCR이 채워졌다고 가정한 구조화 값 사용)

    ctx 키: agreed_hourly_wage, worked_hours[], deposits[](int 합산용),
            deposit_events[{date,amount}], raw_deductions[{name,amount}],
            present_categories(set), gps_logs[{ts,lat,lng,is_mocked}],
            workplace{lat,lng,radius_m}, chat_arrivals[datetime],
            work_start_date, workplace_name, target_lang,
            evidences[{image_bytes,category}] (선택, OCR용)
    """
    llm = get_llm()
    translator = get_translator()
    target_lang = ctx.get("target_lang", "ko")

    # 1단계: OCR + 엔티티 (provider). 로컬 mock은 빈 결과 → 사용자 입력값 사용.
    for ev in ctx.get("evidences", []):
        if ev.get("image_bytes"):
            _ = get_ocr(ev.get("category", "other")).extract(ev["image_bytes"], ev.get("category", "other"))
            # 실제 구현 시 추출 엔티티를 ctx에 병합 (OCR 담당)

    # 2단계: 규칙 기반 차액·공제 (생성형 X)
    w = wage.compute_unpaid(ctx.get("agreed_hourly_wage"), ctx.get("worked_hours", []), ctx.get("deposits", []))
    classified = ded.classify_deductions(ctx.get("raw_deductions", []))

    # 5단계: 누락 체크 (규칙)
    miss = missing.check_missing(set(ctx.get("present_categories", [])))

    # 6단계: GPS 지오펜스 + 교차검증 (규칙)
    gps_result: dict = {}
    wp = ctx.get("workplace")
    if wp and ctx.get("gps_logs"):
        tagged = geofence.tag_logs(ctx["gps_logs"], wp["lat"], wp["lng"], wp.get("radius_m", 50))
        results = geofence.cross_check(tagged, ctx.get("chat_arrivals", []))
        # 버그#6 수정 반영: cross_check는 match=False도 반환하므로 match=True만 카운트
        gps_result = {
            "tagged_count": len(tagged),
            "cross_matches": sum(1 for r in results if r["match"]),
            "cross_mismatches": sum(1 for r in results if not r["match"]),
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

    # 3단계: 번역 + 원문-번역 대조표 (provider, 원문 보존)
    result["translation_pairs"] = tr.build_translation_pairs(ctx, result, translator, target_lang)

    # 4단계: 타임라인 = 규칙 정렬 + LLM 문장화 + 번역 병기 (provider)
    result["timeline"] = tl.build_timeline(ctx, result, llm, translator, target_lang)

    # 7단계 요약: LLM (mock=사실 결합 + 면책)
    result["timeline_summary"] = llm.summarize_case([e["description"] for e in result["timeline"]])

    return result
