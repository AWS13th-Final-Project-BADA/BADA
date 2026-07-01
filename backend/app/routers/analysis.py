"""분석 실행 + 표준 스키마(AnalysisReport) 반환 + 제출용 리포트.

/analyze 와 /analysis 는 동일한 AnalysisReport 스키마를 반환한다(연동 친화).
응답 계약은 schemas_report.AnalysisReport, OpenAPI(/docs)에 자동 노출된다.
제출용 report.html 은 표준 스키마 기반이며, lang!=ko 면 조회 시점에 실시간 번역(다국어).
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import AnalysisResult, Case, TimelineEvent, TranslationPair
from ..schemas_analyze import AnalyzeRequest
from ..schemas_report import AnalysisReport
from ..services import analysis_service, report_builder, s3
from ..services.queue import send_analysis_job

router = APIRouter(prefix="/cases/{case_id}", tags=["analysis"])

DISCLAIMER = report_builder.DISCLAIMER


def _date(s):
    try:
        return date.fromisoformat(s) if s else None
    except Exception:
        return None


@router.post("/analyze")
def analyze(case_id: str, req: AnalyzeRequest | None = None, lang: str = Query("ko"), db: Session = Depends(get_db)):
    """분석 요청 — SQS에 작업을 발행하고 즉시 응답. Worker가 비동기로 처리."""
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")

    # 이미 진행 중이면 중복 요청 방지
    if case.status == "analyzing":
        return {"status": "analyzing", "message": "이미 분석이 진행 중입니다."}

    # SQS 발행 시도
    if settings.sqs_queue_url:
        send_analysis_job(case_id, lang=lang)
        case.status = "analyzing"
        db.commit()
        return {"status": "analyzing", "message": "분석 요청이 접수되었습니다. 잠시 후 결과를 확인할 수 있습니다."}

    # SQS 미설정 (로컬) → 동기 실행 폴백
    import time as _time
    from ..middleware.prometheus import ANALYSIS_RUNS, ANALYSIS_DURATION
    req = req or AnalyzeRequest()
    _start = _time.perf_counter()
    try:
        result = analysis_service.run_analysis(db, case, req, target_lang=lang)
    except Exception:
        ANALYSIS_RUNS.labels(status="error").inc()
        raise
    ANALYSIS_RUNS.labels(status="success").inc()
    ANALYSIS_DURATION.observe(_time.perf_counter() - _start)

    report = report_builder.build_report(case, result, lang=lang, provider_mode=settings.provider_mode)
    report_dict = report.model_dump()

    db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).delete()
    db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).delete()
    db.query(TranslationPair).filter(TranslationPair.case_id == case_id).delete()

    db.add(AnalysisResult(
        case_id=case_id,
        total_expected_wage=result["total_expected_wage"],
        total_received_wage=result["total_received_wage"],
        suspected_unpaid=result["suspected_unpaid"],
        deduction_items=result["deduction_items"],
        calculation_detail={"report": report_dict},
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
    from .notifications import create_notification
    create_notification(db, case.user_id, "analysis_complete", "분석이 완료되었습니다", case_id=case_id)
    return report_dict


def _load_report(case_id: str, db: Session) -> dict:
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    if not ar:
        raise HTTPException(404, "no analysis yet")
    rep = (ar.calculation_detail or {}).get("report")
    if not rep:
        raise HTTPException(409, "report not available (re-run analyze)")
    return rep


@router.get("/analysis")
def get_analysis(case_id: str, db: Session = Depends(get_db)):
    """저장된 분석을 표준 스키마로 반환. pdf_ready 포함."""
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    if not ar:
        raise HTTPException(404, "no analysis yet")
    rep = (ar.calculation_detail or {}).get("report")
    if rep:
        rep["pdf_ready"] = bool(ar.pdf_ko_s3_key)
        return rep
    # Worker가 저장한 형식 (report 키 없음) → 원시 AR 데이터 반환
    return {
        "wage": {
            "expected": ar.total_expected_wage,
            "received": ar.total_received_wage,
            "suspected_unpaid": ar.suspected_unpaid,
        },
        "deduction_items": ar.deduction_items or [],
        "missing": ar.missing_evidences or [],
        "timeline": [
            {"date": str(e.event_date) if e.event_date else None, "type": e.event_type,
             "text": e.description, "text_translated": e.description_translated,
             "confidence": e.confidence}
            for e in db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).all()
        ],
        "narrative": {"summary": ar.timeline_summary or "", "disclaimer": ""},
        "calculation_detail": ar.calculation_detail or {},
        "pdf_ready": bool(ar.pdf_ko_s3_key),
    }


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
    if gps:
        _gps_head = (f"<p>GPS 핑 {gps.get('tagged_count',0)}건 "
                     f"(근무지 안 {gps.get('in_count',0)} · 밖 {gps.get('out_count',0)} · 배제 {gps.get('excluded_count',0)}) · "
                     f"카톡-근무지 교차일치 <b>{gps.get('cross_matches',0)}건</b>"
                     + (f" · 불일치 {gps.get('cross_mismatches',0)}건" if gps.get('cross_mismatches') else "")
                     + "</p>")
        _daily = gps.get("daily") or []
        if _daily:
            _rows = "".join(
                f"<tr><td>{d.get('work_date','')}</td>"
                f"<td style='text-align:center'>{d.get('in_count',0)}</td>"
                f"<td>{(d.get('first_in') or '-')}</td>"
                f"<td>{(d.get('last_out') or '-')}</td>"
                f"<td style='text-align:right'>{d.get('estimated_hours',0)}h"
                + ("" if d.get('hours_method')=='actual_intervals' else " <span class='muted'>(핑 부족)</span>")
                + "</td></tr>"
                for d in _daily)
            _gps_table = (f"<table><tr><th>날짜</th><th>근무지 핑</th><th>최초 체류</th>"
                          f"<th>최종 체류</th><th>추정 체류시간</th></tr>{_rows}</table>")
        else:
            _gps_table = ""
        gps_html = _gps_head + _gps_table
    else:
        gps_html = "<p class='muted'>GPS 데이터 없음</p>"

    computable = wage.get("computable")

    # 리포트 UI 텍스트 다국어 dict
    ui = {
        "ko": {"title":"임금체불 상담 준비 — Evidence Pack","sub_suffix":"상담 준비용(법률자문 아님)","h1":"사건 개요","h2":"핵심 쟁점 요약","h3":"금액 분석","h4":"증거 대조 (검증 포인트)","h5":"법정 기준 점검","h6":"공제 항목","h7":"사건 타임라인","h8":"원문 — 번역 대조","h9":"GPS 정황","h10":"보강하면 좋은 자료","workplace":"사업장","employer":"사업주","period":"근무 기간","hourly":"약속 시급","issues":"문제 유형","ongoing":"진행중/미상","expected":"기대 급여","received":"실수령(입금)","gap":"미지급 의심 금액","gap_none":"입금·근무시간 자료가 부족하여 미지급 금액은 계산하지 않았습니다(확인 필요).","not_confirmed":"확정 아님 · 확인 필요","cmp_th":["비교 항목","값","판정","비고"],"cmp_empty":"대조할 자료가 부족합니다.","ded_th":["항목","분류","금액","출처","확인 필요"],"ded_total":"공제 합계","tl_empty":"날짜 정보 부족","tr_th":["원문(한국어)","번역","증거 유형"],"gps_none":"GPS 데이터 없음","miss_ok":"현재 자료로 충분합니다.","legal_ok":"최저임금 미달·가산수당·과다공제로 확인된 항목이 없습니다.","print":"PDF로 저장 / 인쇄","sum_empty":"(요약 없음)","need":"확인 필요","src":"출처 첨부","sev":{"high":"중요","medium":"확인","low":"참고"},"cmp_st":{"match":"일치","mismatch":"차이","missing":"자료 부족"}},
        "en": {"title":"Wage Consultation Prep — Evidence Pack","sub_suffix":"For consultation prep (not legal advice)","h1":"Case Overview","h2":"Key Issues Summary","h3":"Wage Analysis","h4":"Evidence Comparison (Checkpoints)","h5":"Legal Standards Check","h6":"Deductions","h7":"Case Timeline","h8":"Source — Translation Table","h9":"GPS Context","h10":"Recommended Additional Documents","workplace":"Workplace","employer":"Employer","period":"Work Period","hourly":"Agreed Hourly Wage","issues":"Issue Types","ongoing":"ongoing/unknown","expected":"Expected Pay","received":"Actual Received","gap":"Suspected Unpaid Amount","gap_none":"Insufficient deposit/hours data to calculate unpaid amount (needs review).","not_confirmed":"Not confirmed · needs review","cmp_th":["Item","Values","Status","Note"],"cmp_empty":"Not enough data to compare.","ded_th":["Item","Category","Amount","Source","Review Needed"],"ded_total":"Deduction Total","tl_empty":"Date info insufficient","tr_th":["Original (Korean)","Translation","Evidence Type"],"gps_none":"No GPS data","miss_ok":"Current documents are sufficient.","legal_ok":"No issues found for minimum wage, premium pay, or excessive deductions.","print":"Save as PDF / Print","sum_empty":"(No summary)","need":"needs review","src":"source attached","sev":{"high":"Critical","medium":"Review","low":"Note"},"cmp_st":{"match":"Match","mismatch":"Mismatch","missing":"Insufficient"}},
        "vi": {"title":"Chuẩn bị tư vấn lương — Evidence Pack","sub_suffix":"Chuẩn bị tư vấn (không phải tư vấn pháp lý)","h1":"Tổng quan vụ việc","h2":"Tóm tắt vấn đề chính","h3":"Phân tích lương","h4":"Đối chiếu bằng chứng","h5":"Kiểm tra tiêu chuẩn pháp lý","h6":"Khoản trừ","h7":"Dòng thời gian","h8":"Bảng đối chiếu nguyên bản — dịch","h9":"GPS","h10":"Tài liệu nên bổ sung","workplace":"Nơi làm việc","employer":"Chủ lao động","period":"Thời gian làm việc","hourly":"Lương giờ thỏa thuận","issues":"Loại vấn đề","ongoing":"đang làm/không rõ","expected":"Lương dự kiến","received":"Thực nhận","gap":"Số tiền nghi chưa trả","gap_none":"Thiếu dữ liệu để tính số tiền chưa trả (cần kiểm tra).","not_confirmed":"Chưa xác nhận · cần kiểm tra","cmp_th":["Hạng mục","Giá trị","Trạng thái","Ghi chú"],"cmp_empty":"Không đủ dữ liệu để so sánh.","ded_th":["Khoản","Phân loại","Số tiền","Nguồn","Cần kiểm tra"],"ded_total":"Tổng trừ","tl_empty":"Thiếu thông tin ngày","tr_th":["Nguyên bản","Dịch","Loại bằng chứng"],"gps_none":"Không có dữ liệu GPS","miss_ok":"Tài liệu hiện tại đủ.","legal_ok":"Không phát hiện vấn đề.","print":"Lưu PDF / In","sum_empty":"(Không có tóm tắt)","need":"cần kiểm tra","src":"có nguồn","sev":{"high":"Quan trọng","medium":"Kiểm tra","low":"Tham khảo"},"cmp_st":{"match":"Khớp","mismatch":"Chênh lệch","missing":"Thiếu"}},
        "ja": {"title":"賃金相談準備 — Evidence Pack","sub_suffix":"相談準備用（法律相談ではありません）","h1":"事件概要","h2":"主要争点まとめ","h3":"金額分析","h4":"証拠対照（検証ポイント）","h5":"法定基準チェック","h6":"控除項目","h7":"タイムライン","h8":"原文 — 翻訳対照","h9":"GPS状況","h10":"追加で準備すべき資料","workplace":"職場","employer":"雇用主","period":"勤務期間","hourly":"約束時給","issues":"問題の種類","ongoing":"勤務中/不明","expected":"期待賃金","received":"実受取額","gap":"未払い疑い金額","gap_none":"入金・勤務時間の資料不足で未払い額を計算できませんでした。","not_confirmed":"確定ではない・確認必要","cmp_th":["比較項目","値","判定","備考"],"cmp_empty":"比較する資料が不足しています。","ded_th":["項目","分類","金額","出典","確認必要"],"ded_total":"控除合計","tl_empty":"日付情報不足","tr_th":["原文","翻訳","証拠種類"],"gps_none":"GPSデータなし","miss_ok":"現在の資料で十分です。","legal_ok":"確認された項目はありません。","print":"PDF保存 / 印刷","sum_empty":"(要約なし)","need":"確認必要","src":"出典添付","sev":{"high":"重要","medium":"確認","low":"参考"},"cmp_st":{"match":"一致","mismatch":"差異","missing":"不足"}},
        "th": {"title":"เตรียมปรึกษาเรื่องค่าจ้าง — Evidence Pack","sub_suffix":"เตรียมปรึกษา (ไม่ใช่คำปรึกษาทางกฎหมาย)","h1":"ภาพรวมคดี","h2":"สรุปประเด็นสำคัญ","h3":"วิเคราะห์ค่าจ้าง","h4":"เปรียบเทียบหลักฐาน","h5":"ตรวจสอบมาตรฐานกฎหมาย","h6":"รายการหักเงิน","h7":"ลำดับเหตุการณ์","h8":"ตารางต้นฉบับ — แปล","h9":"GPS","h10":"เอกสารที่ควรเตรียมเพิ่ม","workplace":"สถานที่ทำงาน","employer":"นายจ้าง","period":"ระยะเวลาทำงาน","hourly":"ค่าจ้าง/ชม.","issues":"ประเภทปัญหา","ongoing":"ดำเนินการ/ไม่ทราบ","expected":"ค่าจ้างที่คาดหวัง","received":"ได้รับจริง","gap":"จำนวนเงินที่สงสัยค้างจ่าย","gap_none":"ข้อมูลไม่เพียงพอในการคำนวณ","not_confirmed":"ยังไม่ยืนยัน · ต้องตรวจสอบ","cmp_th":["รายการ","ค่า","สถานะ","หมายเหตุ"],"cmp_empty":"ข้อมูลไม่เพียงพอ","ded_th":["รายการ","ประเภท","จำนวน","แหล่งที่มา","ต้องตรวจสอบ"],"ded_total":"รวมหัก","tl_empty":"ข้อมูลวันที่ไม่เพียงพอ","tr_th":["ต้นฉบับ","แปล","ประเภท"],"gps_none":"ไม่มีข้อมูล GPS","miss_ok":"เอกสารปัจจุบันเพียงพอ","legal_ok":"ไม่พบปัญหา","print":"บันทึก PDF / พิมพ์","sum_empty":"(ไม่มีสรุป)","need":"ต้องตรวจสอบ","src":"แนบแหล่งที่มา","sev":{"high":"สำคัญ","medium":"ตรวจสอบ","low":"หมายเหตุ"},"cmp_st":{"match":"ตรงกัน","mismatch":"ไม่ตรง","missing":"ข้อมูลไม่พอ"}},
    }
    t = ui.get(lang, ui.get("en", ui["ko"]))

    gap_line = (f"<p class='big'>{t['gap']}: {_won(wage.get('suspected_unpaid'))} <span class='muted'>({t['not_confirmed']})</span></p>"
                if computable else
                f"<p class='muted'>{t['gap_none']}</p>")

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
<button onclick="window.print()" style="float:right;padding:8px 14px;cursor:pointer">{t['print']}</button>
<h1>{t['title']}</h1>
<div class="sub">{c.get('workplace') or '-'} · {meta.get('generated_at','')[:10]} · {t['sub_suffix']}</div>
<div class="disc">{tr(narrative.get('disclaimer',''))}</div>

<h2>1. {t['h1']}</h2>
<dl class="kv">
 <dt>{t['workplace']}</dt><dd>{c.get('workplace') or '-'}</dd>
 <dt>{t['employer']}</dt><dd>{c.get('employer') or '-'}</dd>
 <dt>{t['period']}</dt><dd>{period.get('start') or '-'} ~ {period.get('end') or t['ongoing']}</dd>
 <dt>{t['hourly']}</dt><dd>{_won(wage.get('agreed_hourly'))}</dd>
 <dt>{t['issues']}</dt><dd>{', '.join(c.get('issue_types') or []) or '-'}</dd>
</dl>

<h2>2. {t['h2']} <span class="muted" style="font-weight:400;font-size:12px">({t['need']})</span></h2>
<div class="sum">{tr(narrative.get('summary') or t['sum_empty'])}</div>

<h2>3. {t['h3']}</h2>
{gap_line}
<dl class="kv">
 <dt>{t['expected']}</dt><dd>{_won(wage.get('expected'))} <span class="muted">({wage.get('basis','')})</span></dd>
 <dt>{t['received']}</dt><dd>{_won(wage.get('received'))}</dd>
</dl>
{"".join(f'<p class="muted" style="font-size:12px">· {tr(n)}</p>' for n in wage.get('notes', []))}

<h2>4. {t['h4']}</h2>
<table><tr><th>{t['cmp_th'][0]}</th><th>{t['cmp_th'][1]}</th><th>{t['cmp_th'][2]}</th><th>{t['cmp_th'][3]}</th></tr>
{issues or f'<tr><td colspan=4 class="muted">{t["cmp_empty"]}</td></tr>'}</table>

<h2>5. {t['h5']} ({mw.get('year','')} {_won(mw.get('hourly'))})</h2>
<ul>{findings or f'<li class="muted">{t["legal_ok"]}</li>'}</ul>

<h2>6. {t['h6']}</h2>
<table><tr><th>{t['ded_th'][0]}</th><th>{t['ded_th'][1]}</th><th>{t['ded_th'][2]}</th><th>{t['ded_th'][3]}</th><th>{t['ded_th'][4]}</th></tr>
{deds or '<tr><td colspan=5 class="muted">-</td></tr>'}</table>
<p style="text-align:right;font-size:13px">{t['ded_total']}: <b>{ded_total:,}원</b></p>

<h2>7. {t['h7']}</h2>
<ul>{tl or f'<li class="muted">{t["tl_empty"]}</li>'}</ul>

<h2>8. {t['h8']}</h2>
<table><tr><th>{t['tr_th'][0]}</th><th>{t['tr_th'][1]}</th><th>{t['tr_th'][2]}</th></tr>
{trs or '<tr><td colspan=3 class="muted">-</td></tr>'}</table>

<h2>9. {t['h9']}</h2>
{gps_html}

<h2>10. {t['h10']}</h2>
<ul>{miss or f'<li>{t["miss_ok"]}</li>'}</ul>

<div class="foot">BADA · schema {meta.get('schema_version','')} · 언어 {meta.get('lang','')} · 본 문서는 상담 준비용이며 법적 효력을 갖지 않습니다.</div>
</body></html>"""
    return HTMLResponse(html)


@router.get("/report.pdf")
def report_pdf(case_id: str, lang: str = Query("ko"), db: Session = Depends(get_db)):
    """제출용 PDF 다운로드 — 워커가 S3에 저장한 Evidence Pack PDF로 302 redirect(모바일 연동).

    - lang=ko → pdf_ko_s3_key, 그 외(native) → pdf_native_s3_key(없으면 ko 폴백).
    - presigned GET URL은 짧은 만료(security.md §5). PUT 아닌 GET이라 ContentType 불일치 없음.
    - PDF 미생성 시 404 → 모바일은 기존 GET /report.html 로 폴백 가능.
    - 사건 존재만 확인(report.html과 동일 패턴). 행수준 인가는 엔드포인트 공통 과제(security.md §5).
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    if not ar:
        raise HTTPException(404, "no analysis yet")
    key = ar.pdf_native_s3_key if (lang != "ko" and ar.pdf_native_s3_key) else ar.pdf_ko_s3_key
    if not key:
        # 워커가 아직 PDF를 생성하지 않음 → 모바일은 report.html 로 폴백
        raise HTTPException(404, "report pdf not generated yet")
    if not settings.s3_bucket:
        raise HTTPException(409, "s3 not configured")
    import os, boto3
    # report 버킷: S3_REPORT_BUCKET 환경변수 → 없으면 evidence 버킷명에서 추론
    report_bucket = os.environ.get("S3_REPORT_BUCKET") or settings.s3_bucket.replace("-evidence", "-report")
    s3_client = boto3.client("s3", region_name=settings.aws_region)
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": report_bucket, "Key": key},
        ExpiresIn=300,
    )
    return RedirectResponse(url, status_code=302)
