"""분석 실행 + 표준 스키마(AnalysisReport) 반환 + 제출용 리포트.

/analyze 와 /analysis 는 동일한 AnalysisReport 스키마를 반환한다(연동 친화).
응답 계약은 schemas_report.AnalysisReport, OpenAPI(/docs)에 자동 노출된다.
제출용 report.html 은 표준 스키마 기반이며, lang!=ko 면 조회 시점에 실시간 번역(다국어).
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import AnalysisResult, Case, TimelineEvent, TranslationPair
from ..schemas_analyze import AnalyzeRequest
from ..schemas_report import AnalysisReport
from ..services import analysis_service, report_builder

router = APIRouter(prefix="/cases/{case_id}", tags=["analysis"])

DISCLAIMER = report_builder.DISCLAIMER


def _date(s):
    try:
        return date.fromisoformat(s) if s else None
    except Exception:
        return None


@router.post("/analyze", response_model=AnalysisReport)
def analyze(case_id: str, req: AnalyzeRequest | None = None, lang: str = Query("ko"), db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    req = req or AnalyzeRequest()
    result = analysis_service.run_analysis(db, case, req, target_lang=lang)
    report = report_builder.build_report(case, result, lang=lang, provider_mode=settings.provider_mode)
    report_dict = report.model_dump()

    # 영속화 — 표준 리포트 전체 + 조회/리포트용 보조 컬럼
    db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).delete()
    db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).delete()
    db.query(TranslationPair).filter(TranslationPair.case_id == case_id).delete()

    db.add(AnalysisResult(
        case_id=case_id,
        total_expected_wage=result["total_expected_wage"],
        total_received_wage=result["total_received_wage"],
        suspected_unpaid=result["suspected_unpaid"],
        deduction_items=result["deduction_items"],
        calculation_detail={"report": report_dict},   # 표준 스키마를 그대로 보관 → /analysis 동일 반환
        missing_evidences=result["missing_evidences"],
        timeline_summary=result.get("timeline_summary", ""),
    ))
    for e in result["timeline"]:
        db.add(TimelineEvent(case_id=case_id, event_date=_date(e["date"]), event_type=e["type"],
                             description=e["description"], description_translated=e.get("description_translated"),
                             source_evidence_id=e.get("source_evidence_id"), confidence=e.get("confidence", "medium")))
    for p in result["translation_pairs"]:
        db.add(TranslationPair(case_id=case_id, source_text=p["source_text"], translated_text=p["translated_text"],
                               evidence_type=p.get("evidence_type"), related_issue=p.get("related_issue")))
    case.status = "completed"
    db.commit()
    return report


def _load_report(case_id: str, db: Session) -> dict:
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    if not ar:
        raise HTTPException(404, "no analysis yet")
    rep = (ar.calculation_detail or {}).get("report")
    if not rep:
        raise HTTPException(409, "report not available (re-run analyze)")
    return rep


@router.get("/analysis", response_model=AnalysisReport)
def get_analysis(case_id: str, db: Session = Depends(get_db)):
    """저장된 분석을 /analyze 와 동일한 표준 스키마로 반환."""
    return AnalysisReport.model_validate(_load_report(case_id, db))


@router.get("/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db)):
    rows = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).all()
    return [{"id": e.id, "date": str(e.event_date) if e.event_date else None, "type": e.event_type,
             "description": e.description, "description_translated": e.description_translated,
             "source_evidence_id": e.source_evidence_id, "confidence": e.confidence} for e in rows]


@router.get("/translation-pairs")
def get_pairs(case_id: str, db: Session = Depends(get_db)):
    rows = db.query(TranslationPair).filter(TranslationPair.case_id == case_id).all()
    return [{"id": p.id, "source_text": p.source_text, "translated_text": p.translated_text,
             "evidence_type": p.evidence_type, "related_issue": p.related_issue} for p in rows]


@router.get("/missing")
def get_missing(case_id: str, db: Session = Depends(get_db)):
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    return (ar.missing_evidences if ar else []) or []


def _won(n):
    return "확인 불가" if n is None else f"{n:,}원"


@router.get("/report.html", response_class=HTMLResponse)
def report(case_id: str, lang: str = Query("ko"), db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    r = _load_report(case_id, db)

    # 다국어(이해용): lang!=ko 면 표시용 한국어 문장을 조회 시점에 실시간 번역
    is_native = (lang != "ko")
    translator = None
    if is_native:
        import sys
        from pathlib import Path
        _WORKER = Path(__file__).resolve().parents[3] / "worker"
        if str(_WORKER) not in sys.path:
            sys.path.insert(0, str(_WORKER))
        try:
            from providers.translate import get_translator
            translator = get_translator()
        except Exception:
            translator = None

    def tr(text: str) -> str:
        """한국어 원문을 현재 lang으로 번역. ko이거나 실패면 원문 그대로."""
        if not is_native or not text or not translator:
            return text
        try:
            return translator.translate(text, lang)
        except Exception:
            return text

    c = r.get("case", {})
    period = c.get("period", {})
    wage = r.get("wage", {})
    legal = r.get("legal", {})
    mw = legal.get("min_wage", {})
    narrative = r.get("narrative", {})
    meta = r.get("meta", {})

    sev_color = {"high": "#b91c1c", "medium": "#b45309", "low": "#6b7280"}

    issues = "".join(
        f"<tr><td>{tr(c2.get('label',''))}</td>"
        f"<td>{' / '.join(f'{k} {v:,}' if isinstance(v,int) else f'{k} {v}' for k,v in (c2.get('values') or {}).items())}</td>"
        f"<td class='st-{c2.get('status')}'>{ {'match':'일치','mismatch':'차이','missing':'자료 부족'}.get(c2.get('status'),'') }</td>"
        f"<td>{tr(c2.get('note') or '')}</td></tr>"
        for c2 in r.get("comparisons", []))

    findings = "".join(
        f"<li><b style='color:{sev_color.get(f.get('severity'),'#374151')}'>"
        f"[{ {'high':'중요','medium':'확인','low':'참고'}.get(f.get('severity'),'') }]</b> {tr(f.get('message',''))}</li>"
        for f in legal.get("findings", []))

    deds = "".join(
        f"<tr><td>{d.get('name','')}</td><td>{tr(d.get('category',''))}</td>"
        f"<td style='text-align:right'>{d.get('amount',0):,}원</td>"
        f"<td>{tr(', '.join(d.get('sources') or []) or '-')}</td><td>{tr(d.get('verify',''))}</td></tr>"
        for d in r.get("deductions", []))
    ded_total = sum(d.get("amount", 0) for d in r.get("deductions", []))

    tl = "".join(
        f"<li><b>{e.get('date') or '-'}</b> · {tr(e.get('text',''))}"
        + (" <span class='need'>(확인 필요)</span>" if e.get('confidence') == 'low' else "")
        + (" <span class='src'>[출처 첨부]</span>" if e.get('source_evidence_id') else "")
        + "</li>" for e in r.get("timeline", []))

    # 원문-번역 대조: 이해용이면 실시간 번역, 제출용(ko)이면 분석 시 생성된 translated_text
    trs = "".join(
        f"<tr><td>{p.get('source_text','')}</td>"
        f"<td>{tr(p.get('source_text','')) if is_native else p.get('translated_text','')}</td>"
        f"<td>{tr(p.get('evidence_type') or '')}</td></tr>"
        for p in r.get("translations", []))

    miss = "".join(f"<li>[{tr(m.get('item',''))}] {tr(m.get('reason',''))}</li>" for m in r.get("missing", []))
    gps = r.get("gps") or {}
    gps_html = (f"<p>GPS 핑 {gps.get('tagged_count',0)}건 · 카톡-근무지 교차일치 <b>{gps.get('cross_matches',0)}건</b></p>"
                if gps else "<p class='muted'>GPS 데이터 없음</p>")

    computable = wage.get("computable")
    gap_line = (f"<p class='big'>미지급 의심 금액: {_won(wage.get('suspected_unpaid'))} <span class='muted'>(확정 아님 · 확인 필요)</span></p>"
                if computable else
                "<p class='muted'>입금·근무시간 자료가 부족하여 미지급 금액은 계산하지 않았습니다(확인 필요).</p>")

    html = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<title>BADA Evidence Pack — {c.get('workplace') or ''}</title>
<style>
 body{{font-family:'Pretendard','Malgun Gothic',sans-serif;max-width:840px;margin:36px auto;color:#1f2937;line-height:1.65;padding:0 18px}}
 h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#6b7280;font-size:13px;margin-bottom:18px}}
 h2{{font-size:15px;color:#111827;border-bottom:2px solid #e5e7eb;padding-bottom:6px;margin:30px 0 12px}}
 .disc{{background:#f8fafc;border-left:4px solid #94a3b8;padding:12px 14px;font-size:12px;color:#475569;border-radius:6px}}
 table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}}
 th{{background:#f8fafc;text-align:left}} td,th{{border:1px solid #e5e7eb;padding:8px 10px;vertical-align:top}}
 .big{{font-size:18px;font-weight:800;color:#b91c1c;margin:6px 0}}
 .kv{{display:grid;grid-template-columns:140px 1fr;gap:4px 12px;font-size:13px}}
 .kv dt{{color:#6b7280}}
 .sum{{background:#f8fbff;border-left:4px solid #2563eb;padding:14px;font-size:14px;border-radius:6px}}
 ul{{margin:6px 0;padding-left:20px}} li{{margin:3px 0}}
 .muted{{color:#9ca3af}} .need{{color:#b91c1c;font-size:12px}} .src{{color:#9ca3af;font-size:11px}}
 .st-mismatch{{color:#b91c1c;font-weight:700}} .st-match{{color:#047857}} .st-missing{{color:#9ca3af}}
 .foot{{margin-top:30px;color:#9ca3af;font-size:11px;border-top:1px solid #e5e7eb;padding-top:10px}}
 @media print{{button{{display:none}}}}
</style></head><body>
<button onclick="window.print()" style="float:right;padding:8px 14px;cursor:pointer">PDF로 저장 / 인쇄</button>
<h1>임금체불 상담 준비 — Evidence Pack</h1>
<div class="sub">{c.get('workplace') or '사업장 미상'} · 작성일 {meta.get('generated_at','')[:10]} · 상담 준비용(법률자문 아님)</div>
<div class="disc">{tr(narrative.get('disclaimer',''))}</div>

<h2>1. 사건 개요</h2>
<dl class="kv">
 <dt>사업장</dt><dd>{c.get('workplace') or '-'}</dd>
 <dt>사업주</dt><dd>{c.get('employer') or '-'}</dd>
 <dt>근무 기간</dt><dd>{period.get('start') or '-'} ~ {period.get('end') or '진행중/미상'}</dd>
 <dt>약속 시급</dt><dd>{_won(wage.get('agreed_hourly'))}</dd>
 <dt>문제 유형</dt><dd>{', '.join(c.get('issue_types') or []) or '-'}</dd>
</dl>

<h2>2. 핵심 쟁점 요약 <span class="muted" style="font-weight:400;font-size:12px">(자동 정리 · 확인 필요)</span></h2>
<div class="sum">{tr(narrative.get('summary') or '(요약 없음)')}</div>

<h2>3. 금액 분석</h2>
{gap_line}
<dl class="kv">
 <dt>기대 급여</dt><dd>{_won(wage.get('expected'))} <span class="muted">({wage.get('basis','')})</span></dd>
 <dt>실수령(입금)</dt><dd>{_won(wage.get('received'))}</dd>
</dl>
{"".join(f'<p class="muted" style="font-size:12px">· {tr(n)}</p>' for n in wage.get('notes', []))}

<h2>4. 증거 대조 (검증 포인트)</h2>
<table><tr><th>비교 항목</th><th>값</th><th>판정</th><th>비고</th></tr>
{issues or '<tr><td colspan=4 class="muted">대조할 자료가 부족합니다.</td></tr>'}</table>

<h2>5. 법정 기준 점검 ({mw.get('year','')}년 최저임금 {_won(mw.get('hourly'))} 기준)</h2>
<ul>{findings or '<li class="muted">최저임금 미달·가산수당·과다공제로 확인된 항목이 없습니다.</li>'}</ul>

<h2>6. 공제 항목</h2>
<table><tr><th>항목</th><th>분류</th><th>금액</th><th>출처</th><th>확인 필요</th></tr>
{deds or '<tr><td colspan=5 class="muted">-</td></tr>'}</table>
<p style="text-align:right;font-size:13px">공제 합계: <b>{ded_total:,}원</b></p>

<h2>7. 사건 타임라인</h2>
<ul>{tl or '<li class="muted">날짜 정보 부족</li>'}</ul>

<h2>8. 원문 — 번역 대조</h2>
<table><tr><th>원문(한국어)</th><th>번역</th><th>증거 유형</th></tr>
{trs or '<tr><td colspan=3 class="muted">-</td></tr>'}</table>

<h2>9. GPS 정황</h2>
{gps_html}

<h2>10. 보강하면 좋은 자료</h2>
<ul>{miss or '<li>현재 자료로 충분합니다.</li>'}</ul>

<div class="foot">BADA · schema {meta.get('schema_version','')} · 언어 {meta.get('lang','')} · 본 문서는 상담 준비용이며 법적 효력을 갖지 않습니다.</div>
</body></html>"""
    return HTMLResponse(html)
