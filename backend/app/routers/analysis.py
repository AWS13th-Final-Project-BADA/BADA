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
def report(case_id: str, lang: str = Query("ko"), db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    ar = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).first()
    if not case or not ar:
        raise HTTPException(404, "분석 결과가 없습니다.")
    cd = ar.calculation_detail or {}
    is_native = (lang != "ko")  # 모국어 이해용 모드

    # 실시간 번역기 (조회 시점에 번역 — 분석을 다시 돌릴 필요 없음)
    translator = None
    if is_native:
        import sys
        from pathlib import Path
        _WORKER = Path(__file__).resolve().parents[3] / "worker"
        if str(_WORKER) not in sys.path:
            sys.path.insert(0, str(_WORKER))
        from providers.translate import get_translator
        translator = get_translator()

    def tr(text: str) -> str:
        """한국어 원문을 현재 lang으로 번역. ko면 원문 그대로."""
        if not is_native or not text or not translator:
            return text
        return translator.translate(text, lang)

    def won(n):
        return "-" if n is None else f"{n:,}원"

    # 타임라인: 이해용이면 실시간 번역, 제출용이면 원문
    timeline_items = cd.get("timeline", [])
    rows_tl = "".join(
        f"<li><b>{e['date'] or '-'}</b> · {tr(e['description'])}</li>"
        for e in timeline_items)

    # 공제: 이해용이면 항목명·분류·확인사항도 번역
    ded_items = ar.deduction_items or []
    if is_native:
        rows_ded = "".join(
            f"<tr><td>{tr(d['name'])}</td><td>{tr(d['category'])}</td><td style='text-align:right'>{d['amount']:,}원</td><td>{tr(d['check'])}</td></tr>"
            for d in ded_items)
    else:
        rows_ded = "".join(
            f"<tr><td>{d['name']}</td><td>{d['category']}</td><td style='text-align:right'>{d['amount']:,}원</td><td>{d['check']}</td></tr>"
            for d in ded_items)

    # 대조표: source_text(원문 고정) + translated_text(실시간 번역)
    translation_pairs = cd.get("translation_pairs", [])
    evidence_type_map = {
        "en": {"급여명세서/공제": "Payslip/Deduction", "사용자 진술": "User Statement",
               "면책 고지": "Disclaimer", "누락 자료 안내": "Missing Document"},
        "vi": {"급여명세서/공제": "Phiếu lương/Khấu trừ", "사용자 진술": "Lời khai",
               "면책 고지": "Tuyên bố miễn trừ", "누락 자료 안내": "Tài liệu còn thiếu"},
        "th": {"급여명세서/공제": "สลิปเงินเดือน/หักเงิน", "사용자 진술": "คำให้การ",
               "면책 고지": "ข้อจำกัดความรับผิดชอบ", "누락 자료 안내": "เอกสารที่ขาด"},
        "ja": {"급여명세서/공제": "給与明細/控除", "사용자 진술": "利用者陳述",
               "면책 고지": "免責事項", "누락 자료 안내": "不足書類"},
    }
    etype_dict = evidence_type_map.get(lang, {})

    if is_native:
        rows_tr = "".join(
            f"<tr><td>{p['source_text']}</td><td><b>{tr(p['source_text'])}</b></td><td>{etype_dict.get(p.get('evidence_type',''), p.get('evidence_type',''))}</td></tr>"
            for p in translation_pairs)
    else:
        rows_tr = "".join(
            f"<tr><td>{p['source_text']}</td><td>{p['source_text']}</td><td>{p.get('evidence_type','')}</td></tr>"
            for p in translation_pairs)

    # 누락 자료: 이해용이면 번역
    missing_items = ar.missing_evidences or []
    if is_native:
        rows_miss = "".join(f"<li>[{tr(m['item'])}] {tr(m['reason'])}</li>" for m in missing_items)
    else:
        rows_miss = "".join(f"<li>[{m['item']}] {m['reason']}</li>" for m in missing_items)

    gps = cd.get("gps") or {}
    gps_html = (f"<p>GPS 핑 {gps.get('tagged_count', 0)}건 · 카톡-근무지 교차일치 {gps.get('cross_matches', 0)}건</p>"
                if gps else "")

    # UI 텍스트
    ui = {
        "ko": {
            "title": "BADA Evidence Pack (상담 준비용 증거 정리)",
            "disc": "본 자료는 법률자문이 아닌 상담 준비용 증거 정리 자료입니다. 위법·체불 여부와 금액을 확정하지 않으며, 최종 판단은 고용노동부 또는 전문기관에서 확인해야 합니다.",
            "sec1": "1. 사건 요약", "sec2": "2. 사건 타임라인", "sec3": "3. 공제 항목 정리",
            "sec4": "4. 원문-번역 대조표", "sec5": "5. GPS 정황", "sec6": "6. 더 준비하면 좋은 자료",
            "workplace": "사업장", "employer": "사업주", "period": "근무기간",
            "hourly": "약속 시급", "suspected": "미지급 의심 금액", "confirm": "확인 필요",
            "expected": "기대 급여", "received": "실제 수령",
            "print_btn": "PDF로 저장 / 인쇄", "no_date": "(날짜 정보 부족)", "enough": "충분합니다.",
            "th_item": "항목", "th_cat": "분류", "th_amount": "금액", "th_check": "확인 필요",
            "th_source": "원문", "th_trans": "번역", "th_type": "증거유형",
            "no_gps": "(GPS 데이터 없음)", "ongoing": "진행중",
        },
        "en": {
            "title": "BADA Evidence Pack (Consultation Prep)",
            "disc": "This document is NOT legal advice. It organizes evidence for consultation. Final judgment must be confirmed by the Labor Office or a professional.",
            "sec1": "1. Case Summary", "sec2": "2. Case Timeline", "sec3": "3. Deductions",
            "sec4": "4. Source-Translation Table", "sec5": "5. GPS Context", "sec6": "6. Recommended Additional Documents",
            "workplace": "Workplace", "employer": "Employer", "period": "Work period",
            "hourly": "Agreed hourly wage", "suspected": "Suspected unpaid amount", "confirm": "needs review",
            "expected": "Expected pay", "received": "Actual received",
            "print_btn": "Save as PDF / Print", "no_date": "(Date info insufficient)", "enough": "Sufficient.",
            "th_item": "Item", "th_cat": "Category", "th_amount": "Amount", "th_check": "Review needed",
            "th_source": "Original", "th_trans": "Translation", "th_type": "Evidence type",
            "no_gps": "(No GPS data)", "ongoing": "ongoing",
        },
        "vi": {
            "title": "BADA Evidence Pack (Chuẩn bị tư vấn)",
            "disc": "Tài liệu này KHÔNG phải tư vấn pháp lý. Nó sắp xếp bằng chứng để chuẩn bị tư vấn. Quyết định cuối cùng phải được xác nhận bởi Sở Lao động hoặc chuyên gia.",
            "sec1": "1. Tóm tắt vụ việc", "sec2": "2. Dòng thời gian", "sec3": "3. Khoản trừ",
            "sec4": "4. Bảng đối chiếu nguyên bản-dịch", "sec5": "5. GPS", "sec6": "6. Tài liệu nên bổ sung",
            "workplace": "Nơi làm việc", "employer": "Chủ lao động", "period": "Thời gian làm việc",
            "hourly": "Lương giờ thỏa thuận", "suspected": "Số tiền nghi chưa trả", "confirm": "cần kiểm tra",
            "expected": "Lương dự kiến", "received": "Thực nhận",
            "print_btn": "Lưu PDF / In", "no_date": "(Thiếu thông tin ngày)", "enough": "Đủ.",
            "th_item": "Khoản", "th_cat": "Phân loại", "th_amount": "Số tiền", "th_check": "Cần kiểm tra",
            "th_source": "Nguyên bản", "th_trans": "Dịch", "th_type": "Loại bằng chứng",
            "no_gps": "(Không có dữ liệu GPS)", "ongoing": "đang làm",
        },
        "id": {
            "title": "BADA Evidence Pack (Persiapan Konsultasi)",
            "disc": "Dokumen ini BUKAN nasihat hukum. Ini menyusun bukti untuk persiapan konsultasi. Keputusan akhir harus dikonfirmasi oleh Dinas Tenaga Kerja atau profesional.",
            "sec1": "1. Ringkasan Kasus", "sec2": "2. Timeline", "sec3": "3. Potongan",
            "sec4": "4. Tabel Sumber-Terjemahan", "sec5": "5. GPS", "sec6": "6. Dokumen Tambahan yang Disarankan",
            "workplace": "Tempat Kerja", "employer": "Pemberi Kerja", "period": "Periode Kerja",
            "hourly": "Upah per jam yang disepakati", "suspected": "Jumlah yang diduga belum dibayar", "confirm": "perlu diperiksa",
            "expected": "Gaji diharapkan", "received": "Diterima aktual",
            "print_btn": "Simpan PDF / Cetak", "no_date": "(Info tanggal tidak cukup)", "enough": "Cukup.",
            "th_item": "Item", "th_cat": "Kategori", "th_amount": "Jumlah", "th_check": "Perlu diperiksa",
            "th_source": "Asli", "th_trans": "Terjemahan", "th_type": "Jenis bukti",
            "no_gps": "(Tidak ada data GPS)", "ongoing": "berlangsung",
        },
        "km": {
            "title": "BADA Evidence Pack (រៀបចំពិគ្រោះ)",
            "disc": "ឯកសារនេះមិនមែនជាការប្រឹក្សាផ្លូវច្បាប់ទេ។ វារៀបចំភស្តុតាងសម្រាប់ការពិគ្រោះ។ ការវិនិច្ឆ័យចុងក្រោយត្រូវបញ្ជាក់ដោយការិយាល័យពលកម្មឬអ្នកជំនាញ។",
            "sec1": "1. សង្ខេបករណី", "sec2": "2. បន្ទាត់ពេលវេលា", "sec3": "3. ការកាត់ប្រាក់",
            "sec4": "4. តារាងដើម-បកប្រែ", "sec5": "5. GPS", "sec6": "6. ឯកសារបន្ថែមដែលគួររៀបចំ",
            "workplace": "កន្លែងធ្វើការ", "employer": "និយោជក", "period": "រយៈពេលការងារ",
            "hourly": "ប្រាក់ឈ្នួលក្នុងមួយម៉ោង", "suspected": "ចំនួនសង្ស័យមិនបានបង់", "confirm": "ត្រូវពិនិត្យ",
            "expected": "ប្រាក់ឈ្នួលរំពឹង", "received": "ទទួលបានពិត",
            "print_btn": "រក្សាទុក PDF / បោះពុម្ព", "no_date": "(ព័ត៌មានកាលបរិច្ឆេទមិនគ្រប់គ្រាន់)", "enough": "គ្រប់គ្រាន់។",
            "th_item": "មុខ", "th_cat": "ប្រភេទ", "th_amount": "ចំនួន", "th_check": "ត្រូវពិនិត្យ",
            "th_source": "ដើម", "th_trans": "បកប្រែ", "th_type": "ប្រភេទភស្តុតាង",
            "no_gps": "(គ្មានទិន្នន័យ GPS)", "ongoing": "កំពុងបន្ត",
        },
        "ne": {
            "title": "BADA Evidence Pack (परामर्श तयारी)",
            "disc": "यो कागजात कानूनी सल्लाह होइन। परामर्शको तयारीको लागि प्रमाण मिलाउँछ। अन्तिम निर्णय श्रम कार्यालय वा विशेषज्ञबाट पुष्टि गर्नुपर्छ।",
            "sec1": "1. केस सारांश", "sec2": "2. समयरेखा", "sec3": "3. कटौती",
            "sec4": "4. स्रोत-अनुवाद तालिका", "sec5": "5. GPS", "sec6": "6. थप कागजात सिफारिस",
            "workplace": "कार्यस्थल", "employer": "रोजगारदाता", "period": "काम अवधि",
            "hourly": "सहमत प्रति घण्टा ज्याला", "suspected": "बाँकी शंकास्पद रकम", "confirm": "जाँच आवश्यक",
            "expected": "अपेक्षित तलब", "received": "वास्तविक प्राप्त",
            "print_btn": "PDF बचत / प्रिन्ट", "no_date": "(मिति जानकारी अपर्याप्त)", "enough": "पर्याप्त।",
            "th_item": "विवरण", "th_cat": "वर्ग", "th_amount": "रकम", "th_check": "जाँच आवश्यक",
            "th_source": "मूल", "th_trans": "अनुवाद", "th_type": "प्रमाण प्रकार",
            "no_gps": "(GPS डाटा छैन)", "ongoing": "जारी",
        },
        "th": {
            "title": "BADA Evidence Pack (เตรียมเอกสารเพื่อปรึกษา)",
            "disc": "เอกสารนี้ไม่ใช่คำปรึกษาทางกฎหมาย เป็นการจัดระเบียบหลักฐานเพื่อเตรียมปรึกษา การตัดสินขั้นสุดท้ายต้องได้รับการยืนยันจากสำนักงานแรงงานหรือผู้เชี่ยวชาญ",
            "sec1": "1. สรุปคดี", "sec2": "2. ลำดับเหตุการณ์", "sec3": "3. รายการหักเงิน",
            "sec4": "4. ตารางเปรียบเทียบต้นฉบับ-แปล", "sec5": "5. GPS", "sec6": "6. เอกสารที่ควรเตรียมเพิ่ม",
            "workplace": "สถานที่ทำงาน", "employer": "นายจ้าง", "period": "ระยะเวลาทำงาน",
            "hourly": "ค่าจ้างรายชั่วโมงที่ตกลง", "suspected": "จำนวนเงินที่สงสัยว่าค้างจ่าย", "confirm": "ต้องตรวจสอบ",
            "expected": "ค่าจ้างที่คาดหวัง", "received": "ที่ได้รับจริง",
            "print_btn": "บันทึก PDF / พิมพ์", "no_date": "(ข้อมูลวันที่ไม่เพียงพอ)", "enough": "เพียงพอ",
            "th_item": "รายการ", "th_cat": "ประเภท", "th_amount": "จำนวนเงิน", "th_check": "ต้องตรวจสอบ",
            "th_source": "ต้นฉบับ", "th_trans": "แปล", "th_type": "ประเภทหลักฐาน",
            "no_gps": "(ไม่มีข้อมูล GPS)", "ongoing": "ดำเนินการอยู่",
        },
        "ja": {
            "title": "BADA Evidence Pack（相談準備用証拠整理）",
            "disc": "本資料は法律相談ではなく、相談準備のための証拠整理資料です。違法・未払いの有無と金額を確定するものではなく、最終判断は労働基準監督署または専門機関で確認してください。",
            "sec1": "1. 事件概要", "sec2": "2. タイムライン", "sec3": "3. 控除項目",
            "sec4": "4. 原文・翻訳対照表", "sec5": "5. GPS状況", "sec6": "6. 追加で準備すべき資料",
            "workplace": "職場", "employer": "雇用主", "period": "勤務期間",
            "hourly": "約束時給", "suspected": "未払い疑い金額", "confirm": "確認必要",
            "expected": "期待賃金", "received": "実受取額",
            "print_btn": "PDF保存 / 印刷", "no_date": "（日付情報不足）", "enough": "十分です。",
            "th_item": "項目", "th_cat": "分類", "th_amount": "金額", "th_check": "確認必要",
            "th_source": "原文", "th_trans": "翻訳", "th_type": "証拠種類",
            "no_gps": "（GPSデータなし）", "ongoing": "勤務中",
        },
    }
    t = ui.get(lang, ui["ko"])

    # 인쇄 버튼: 항상 한국어 제출용 리포트로 연결
    print_url = f"/cases/{case_id}/report.html?lang=ko"

    html = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<title>BADA Evidence Pack - {case.workplace_name or ''}</title>
<style>
 body{{font-family:'Malgun Gothic','Noto Sans',sans-serif;max-width:800px;margin:40px auto;color:#1a1a1a;line-height:1.6}}
 h1{{font-size:20px}} h2{{font-size:15px;border-bottom:2px solid #333;padding-bottom:4px;margin-top:26px}}
 .disc{{background:#f5f5f5;padding:10px;border-left:4px solid #888;font-size:12px;color:#555}}
 table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{border:1px solid #ccc;padding:6px}}
 .big{{font-size:18px;font-weight:bold;color:#b00}} @media print{{.no-print{{display:none}}}}
</style></head><body>
<div class="no-print" style="float:right">
<button onclick="window.open('{print_url}','_blank')" style="padding:8px 14px;margin-right:6px">{t['print_btn']} (KO)</button>
</div>
<h1>{t['title']}</h1>
<div class="disc">{t['disc']}</div>
<h2>{t['sec1']}</h2>
<p>{t['workplace']}: {case.workplace_name or '-'} / {t['employer']}: {case.employer_name or '-'}<br>
{t['period']}: {case.work_start_date or '-'} ~ {case.work_end_date or t['ongoing']} / {t['hourly']}: {won(case.agreed_hourly_wage)}</p>
<p class="big">{t['suspected']}: {won(ar.suspected_unpaid)} ({t['confirm']})</p>
<p>{t['expected']} {won(ar.total_expected_wage)} / {t['received']} {won(ar.total_received_wage)}</p>
<h2>{t['sec2']}</h2><ul>{rows_tl or f"<li>{t['no_date']}</li>"}</ul>
<h2>{t['sec3']}</h2><table><tr><th>{t['th_item']}</th><th>{t['th_cat']}</th><th>{t['th_amount']}</th><th>{t['th_check']}</th></tr>{rows_ded}</table>
<h2>{t['sec4']}</h2><table><tr><th>{t['th_source']}</th><th>{t['th_trans']}</th><th>{t['th_type']}</th></tr>{rows_tr or '<tr><td colspan=3>-</td></tr>'}</table>
<h2>{t['sec5']}</h2>{gps_html or f"<p>{t['no_gps']}</p>"}
<h2>{t['sec6']}</h2><ul>{rows_miss or f"<li>{t['enough']}</li>"}</ul>
</body></html>"""
    return HTMLResponse(html)
