"""분석 실행(동기) + 결과/타임라인/대조표/누락 조회 + 제출용 리포트(HTML)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AnalysisResult, Case, Evidence, TimelineEvent, TranslationPair
from ..schemas_analyze import AnalyzeRequest
from ..services import analysis_service

router = APIRouter(prefix="/cases/{case_id}", tags=["analysis"])


def _date(s):
    try:
        return date.fromisoformat(s) if s else None
    except Exception:
        return None


@router.post("/analyze")
def analyze(case_id: str, req: AnalyzeRequest, lang: str = Query("ko"), db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    cats = {e.category for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()}
    result = analysis_service.run_analysis(case, cats, req, target_lang=lang)

    # 기존 결과/행 갈아끼우기
    db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).delete()
    db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).delete()
    db.query(TranslationPair).filter(TranslationPair.case_id == case_id).delete()

    db.add(AnalysisResult(
        case_id=case_id,
        total_expected_wage=result["total_expected_wage"],
        total_received_wage=result["total_received_wage"],
        suspected_unpaid=result["suspected_unpaid"],
        deduction_items=result["deduction_items"],
        calculation_detail={"wage": result["calculation_detail"], "gps": result["gps"],
                            "timeline": result["timeline"], "notes": result["notes"],
                            "translation_pairs": result["translation_pairs"],
                            "summary": result.get("timeline_summary", "")},
        missing_evidences=result["missing_evidences"],
        timeline_summary=result.get("timeline_summary", ""),
    ))
    for e in result["timeline"]:
        db.add(TimelineEvent(case_id=case_id, event_date=_date(e["date"]), event_type=e["type"],
                             description=e["description"], description_translated=e.get("description_translated")))
    for p in result["translation_pairs"]:
        db.add(TranslationPair(case_id=case_id, source_text=p["source_text"], translated_text=p["translated_text"],
                               evidence_type=p.get("evidence_type"), related_issue=p.get("related_issue")))
    case.status = "completed"
    db.commit()
    return result


@router.get("/analysis")
def get_analysis(case_id: str, db: Session = Depends(get_db)):
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    if not ar:
        raise HTTPException(404, "no analysis yet")
    cd = ar.calculation_detail or {}
    return {
        "total_expected_wage": ar.total_expected_wage,
        "total_received_wage": ar.total_received_wage,
        "suspected_unpaid": ar.suspected_unpaid,
        "deduction_items": ar.deduction_items,
        "missing_evidences": ar.missing_evidences,
        "timeline": cd.get("timeline", []),
        "translation_pairs": cd.get("translation_pairs", []),
        "gps": cd.get("gps", {}),
        "notes": cd.get("notes", []),
        "timeline_summary": cd.get("summary", ""),
    }


@router.get("/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db)):
    rows = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).all()
    return [{"id": e.id, "date": str(e.event_date) if e.event_date else None, "type": e.event_type,
             "description": e.description, "description_translated": e.description_translated,
             "confidence": e.confidence} for e in rows]


@router.get("/translation-pairs")
def get_pairs(case_id: str, db: Session = Depends(get_db)):
    rows = db.query(TranslationPair).filter(TranslationPair.case_id == case_id).all()
    return [{"id": p.id, "source_text": p.source_text, "translated_text": p.translated_text,
             "evidence_type": p.evidence_type, "related_issue": p.related_issue} for p in rows]


@router.get("/missing")
def get_missing(case_id: str, db: Session = Depends(get_db)):
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    return (ar.missing_evidences if ar else []) or []


@router.get("/report.html", response_class=HTMLResponse)
def report(case_id: str, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    if not case or not ar:
        raise HTTPException(404, "분석 결과가 없습니다.")
    cd = ar.calculation_detail or {}

    def won(n):
        return "-" if n is None else f"{n:,}원"

    rows_ded = "".join(
        f"<tr><td>{d['name']}</td><td>{d['category']}</td><td style='text-align:right'>{d['amount']:,}원</td><td>{d['check']}</td></tr>"
        for d in (ar.deduction_items or []))
    rows_tl = "".join(f"<li><b>{e['date'] or '-'}</b> · {e['description']}</li>" for e in cd.get("timeline", []))
    rows_tr = "".join(
        f"<tr><td>{p['source_text']}</td><td>{p['translated_text']}</td><td>{p.get('evidence_type','')}</td></tr>"
        for p in cd.get("translation_pairs", []))
    rows_miss = "".join(f"<li>[{m['item']}] {m['reason']}</li>" for m in (ar.missing_evidences or []))
    gps = cd.get("gps") or {}
    gps_html = (f"<p>GPS 핑 {gps.get('tagged_count', 0)}건 · 카톡-근무지 교차일치 {gps.get('cross_matches', 0)}건</p>"
                if gps else "")

    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>BADA Evidence Pack - {case.workplace_name or ''}</title>
<style>
 body{{font-family:'Malgun Gothic',sans-serif;max-width:800px;margin:40px auto;color:#1a1a1a;line-height:1.6}}
 h1{{font-size:20px}} h2{{font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-top:26px}}
 .disc{{background:#f5f5f5;padding:10px;border-left:4px solid #888;font-size:12px;color:#555}}
 table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{border:1px solid #ccc;padding:6px}}
 .big{{font-size:18px;font-weight:bold;color:#b00}} @media print{{button{{display:none}}}}
</style></head><body>
<button onclick="window.print()" style="float:right;padding:8px 14px">PDF로 저장 / 인쇄</button>
<h1>BADA Evidence Pack (상담 준비용 증거 정리)</h1>
<div class="disc">본 자료는 법률자문이 아닌 상담 준비용 증거 정리 자료입니다.
위법·체불 여부와 금액을 확정하지 않으며, 최종 판단은 고용노동부 또는 전문기관에서 확인해야 합니다.</div>
<h2>1. 사건 요약</h2>
<p>사업장: {case.workplace_name or '-'} / 사업주: {case.employer_name or '-'}<br>
근무기간: {case.work_start_date or '-'} ~ {case.work_end_date or '진행중'} / 약속 시급: {won(case.agreed_hourly_wage)}</p>
<p class="big">미지급 의심 금액: {won(ar.suspected_unpaid)} (확인 필요)</p>
<p>기대 급여 {won(ar.total_expected_wage)} / 실제 수령 {won(ar.total_received_wage)}</p>
<h2>2. 사건 타임라인</h2><ul>{rows_tl or '<li>(날짜 정보 부족)</li>'}</ul>
<h2>3. 공제 항목 정리</h2><table><tr><th>항목</th><th>분류</th><th>금액</th><th>확인 필요</th></tr>{rows_ded}</table>
<h2>4. 원문-번역 대조표</h2><table><tr><th>원문</th><th>번역</th><th>증거유형</th></tr>{rows_tr or '<tr><td colspan=3>-</td></tr>'}</table>
<h2>5. GPS 정황</h2>{gps_html or '<p>(GPS 데이터 없음)</p>'}
<h2>6. 더 준비하면 좋은 자료</h2><ul>{rows_miss or '<li>충분합니다.</li>'}</ul>
</body></html>"""
    return HTMLResponse(html)
