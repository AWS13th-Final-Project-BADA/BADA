"""워커 분석 결과(dict) → 표준 AnalysisReport 로 매핑(직렬화 계층).

워커는 계산만 한다. 여기서 '연동용 계약 모양'으로 정리한다.
/analyze 와 /analysis 가 동일한 함수를 거쳐 같은 스키마를 반환하도록 한다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..schemas_report import (
    SCHEMA_VERSION, AnalysisReport, CaseInfo, Comparison, Deduction, Finding,
    Gps, GpsDaySummary, Legal, Meta, MinWage, Narrative, Period, TimelineItem,
    TranslationItem, Wage, MissingItem,
)

DISCLAIMER = ("본 자료는 법률자문이 아닌 상담 준비용 증거 정리 자료입니다. "
              "위법·체불 여부와 금액을 확정하지 않으며, 최종 판단은 고용노동부 또는 전문기관에서 확인해야 합니다.")

# 워커 finding.level → 표준 severity (동일하지만 명시적으로 매핑)
_SEV = {"high": "high", "medium": "medium", "low": "low"}


def build_report(case, result: dict, lang: str = "ko", provider_mode: str = "local") -> AnalysisReport:
    """case(ORM) + 워커 result(dict) → AnalysisReport."""
    cd = result.get("calculation_detail") or {}

    expected = result.get("total_expected_wage")
    received = result.get("total_received_wage")
    suspected = result.get("suspected_unpaid")

    wage = Wage(
        computable=suspected is not None,
        agreed_hourly=cd.get("hourly_wage") or getattr(case, "agreed_hourly_wage", None),
        expected=expected, received=received, suspected_unpaid=suspected,
        basis=cd.get("formula") or "기대급여 = 시급 × 근무시간합; 미지급의심 = 기대 − 실수령",
        notes=result.get("notes", []) or [],
    )

    deductions = [
        Deduction(name=d.get("name", ""), category=d.get("category", "기타공제"),
                  amount=int(d.get("amount", 0)), sources=d.get("sources", []) or [],
                  verify=d.get("check", ""))
        for d in (result.get("deduction_items") or [])
    ]

    comparisons = [
        Comparison(key=c.get("key", ""), label=c.get("label", ""),
                   status=c.get("status", "missing"), values=c.get("values", {}) or {},
                   note=c.get("note") or None)
        for c in (result.get("compare") or [])
    ]

    lg = result.get("legal") or {}
    legal = Legal(
        min_wage=MinWage(year=lg.get("min_wage_year") or 0, hourly=lg.get("min_wage") or 0),
        findings=[
            Finding(type=f.get("type"), severity=_SEV.get(f.get("level"), "medium"),
                    message=f.get("note", ""),
                    amount=f.get("shortfall_total") or f.get("estimated_premium") or f.get("actual"))
            for f in (lg.get("findings") or [])
        ],
    )

    timeline = [
        TimelineItem(date=e.get("date"), type=e.get("type", "event"),
                     text=e.get("description", ""), text_translated=e.get("description_translated"),
                     source_evidence_id=e.get("source_evidence_id"),
                     confidence=e.get("confidence", "medium"))
        for e in (result.get("timeline") or [])
    ]

    translations = [
        TranslationItem(source_text=p.get("source_text", ""), translated_text=p.get("translated_text", ""),
                        evidence_type=p.get("evidence_type"), related_issue=p.get("related_issue"))
        for p in (result.get("translation_pairs") or [])
    ]

    missing = [MissingItem(item=m.get("item", ""), reason=m.get("reason", ""))
               for m in (result.get("missing_evidences") or [])]

    g = result.get("gps") or {}
    gps = Gps(
        tagged_count=g.get("tagged_count", 0),
        excluded_count=g.get("excluded_count", 0),
        in_count=g.get("in_count", 0),
        out_count=g.get("out_count", 0),
        cross_matches=g.get("cross_matches", 0),
        cross_mismatches=g.get("cross_mismatches", 0),
        daily=[GpsDaySummary(**d) for d in (g.get("daily") or [])],
    ) if g else None

    return AnalysisReport(
        schema_version=SCHEMA_VERSION,
        case=CaseInfo(
            id=case.id, workplace=case.workplace_name, employer=case.employer_name,
            period=Period(start=str(case.work_start_date) if case.work_start_date else None,
                          end=str(case.work_end_date) if case.work_end_date else None),
            issue_types=case.issue_types or [],
        ),
        wage=wage, deductions=deductions, comparisons=comparisons, legal=legal,
        timeline=timeline, translations=translations, missing=missing, gps=gps,
        narrative=Narrative(summary=result.get("timeline_summary", "") or "", disclaimer=DISCLAIMER),
        meta=Meta(schema_version=SCHEMA_VERSION,
                  generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  lang=lang, provider_mode=provider_mode),
    )
