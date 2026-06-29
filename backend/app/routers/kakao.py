"""카카오 i 오픈빌더 스킬 서버 — BADA (다국어 + 로그인 연동 + 체불 진단).

기능
  1) 체불 간이진단   : 시급 ↔ 최저임금 비교(rules.legal). "당하는지도 모르는 사람" 발견용.
  2) 내 사건 현황     : 로그인 연동 시 그 사용자, 아니면 최근 사건(DB) 조회.
  3) 증거 체크리스트  : 필수 자료 대비 진행률.
  4) 증거 수집 가이드 : 항목별 안내.
  5) 신고 절차 안내.
  6) 계정 연동        : 앱에서 발급한 연동코드를 입력하면 카톡 사용자 ↔ BADA 계정 매핑.
다국어: 한국어/베트남어/영어. 발화 언어를 감지해 그 언어로 응답(+언어 전환 버튼).

원칙: LLM 미사용(5초 안전) · 법적 판단/대리 안 함 · 정보 제공만(법률자문 아님).
"""
import os
import re
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from ..db import SessionLocal
from ..models import AnalysisResult, Case, Evidence

# worker(rules) 경로 — 최저임금 등 룰 재활용
_WORKER = Path(__file__).resolve().parents[3] / "worker"
if str(_WORKER) not in sys.path:
    sys.path.insert(0, str(_WORKER))

router = APIRouter(prefix="/kakao", tags=["kakao"])
_MAX_TEXT = 950
LANGS = ("ko", "vi", "en")

# ── 카테고리 라벨(언어별) ──
CATEGORY = {
    "ko": {"contract": "근로계약서", "schedule": "근무표", "payment": "입금내역",
           "chat": "대화 캡처", "statement": "급여명세서", "other": "기타 자료"},
    "vi": {"contract": "Hợp đồng lao động", "schedule": "Bảng chấm công", "payment": "Sao kê chuyển khoản",
           "chat": "Ảnh tin nhắn", "statement": "Bảng lương", "other": "Tài liệu khác"},
    "en": {"contract": "Employment contract", "schedule": "Work schedule", "payment": "Bank transfer record",
           "chat": "Chat screenshot", "statement": "Payslip", "other": "Other"},
}
_REQUIRED = ["contract", "statement", "payment", "schedule"]

DISCLAIMER = {
    "ko": "※ 일반 정보 안내이며 법률자문이 아닙니다.",
    "vi": "※ Đây là thông tin chung, không phải tư vấn pháp lý.",
    "en": "※ General information only, not legal advice.",
}

# ── 메뉴(언어별): (버튼라벨, 보낼말) ── walk-in 친화 5개. 연동은 필요할 때만(게이트).
MENU = {
    "ko": [("내 시급 확인", "내 시급 확인"), ("준비 상태 체크", "준비 상태 체크"), ("신고 방법", "신고 방법"),
           ("내 사건 현황", "내 사건 현황"), ("🌐 Language", "language")],
    "vi": [("Kiểm tra lương", "Kiểm tra lương"), ("Tình trạng chuẩn bị", "Tình trạng chuẩn bị"),
           ("Cách khiếu nại", "Cách khiếu nại"), ("Hồ sơ của tôi", "Hồ sơ của tôi"), ("🌐 언어", "language")],
    "en": [("Wage check", "Wage check"), ("Readiness check", "Readiness check"), ("How to report", "How to report"),
           ("My case", "My case"), ("🌐 언어", "language")],
}

# 첫 진입 캐러셀(여러 장 카드): 카드1=소개+핵심 버튼, 카드2=메뉴 안내+버튼. 연동은 '내 자료 연결' 버튼으로 부드럽게.
WELCOME_CARDS = {
    "ko": [
        ("BADA는 처음이신가요? 🌊",
         "임금을 제대로 받고 있는지 확인하고, 신고에 필요한 증거 준비를 도와드려요.",
         [("내 시급 확인", "내 시급 확인"), ("준비 상태 체크", "준비 상태 체크"), ("🔗 내 자료 연결", "연동")]),
        ("무엇을 도와드릴까요?",
         "아래에서 필요한 걸 골라보세요. 로그인 없이도 시급 확인·신고 방법을 쓸 수 있어요.",
         [("신고 방법", "신고 방법"), ("내 사건 현황", "내 사건 현황"), ("오늘 할 일", "오늘")]),
    ],
    "vi": [
        ("Bạn mới dùng BADA? 🌊",
         "Kiểm tra bạn có được trả lương đúng không và giúp chuẩn bị bằng chứng để khiếu nại.",
         [("Kiểm tra lương", "Kiểm tra lương"), ("Tình trạng chuẩn bị", "Tình trạng chuẩn bị"), ("🔗 Kết nối tài liệu", "kết nối")]),
        ("Tôi có thể giúp gì?",
         "Chọn mục bên dưới. Không cần đăng nhập vẫn kiểm tra lương·cách khiếu nại được.",
         [("Cách khiếu nại", "Cách khiếu nại"), ("Hồ sơ của tôi", "Hồ sơ của tôi"), ("Việc hôm nay", "hôm nay")]),
    ],
    "en": [
        ("New to BADA? 🌊",
         "Check whether you're paid correctly and prepare the evidence you need to report unpaid wages.",
         [("Wage check", "Wage check"), ("Readiness check", "Readiness check"), ("🔗 Connect my files", "connect")]),
        ("How can I help?",
         "Pick what you need below. Wage check and how-to-report work without login.",
         [("How to report", "How to report"), ("My case", "My case"), ("Today's tasks", "today")]),
    ],
}

# 연동 안내 — 첫 화면·'연동' 발화에서 친절·예쁘게. (라벨/보낼말/카드)
CONNECT_BTN = {"ko": "🔗 내 자료 연결", "vi": "🔗 Kết nối tài liệu", "en": "🔗 Connect my files"}
CONNECT_MSG = {"ko": "연동", "vi": "kết nối", "en": "connect"}
LINK_HELP = {
    "ko": ("🔗 내 자료와 연결하기",
           "앱에 올린 서류를 챗봇에서 바로 확인할 수 있어요.\n\n"
           "① BADA 앱 로그인\n② '카카오 연동'에서 6자리 코드 받기\n③ 코드를 여기에 붙여넣고 전송\n\n"
           "한 번만 연결하면 끝이에요 😊"),
    "vi": ("🔗 Kết nối tài liệu của bạn",
           "Xem tài liệu đã tải lên ngay trong chatbot.\n\n"
           "① Đăng nhập app BADA\n② Lấy mã 6 ký tự ở 'Kết nối Kakao'\n③ Dán mã vào đây và gửi\n\n"
           "Chỉ cần kết nối một lần 😊"),
    "en": ("🔗 Connect your files",
           "See the files you uploaded right here in the chat.\n\n"
           "① Log in to the BADA app\n② Get a 6-character code in 'Kakao link'\n③ Paste the code here and send\n\n"
           "Connect once and you're done 😊"),
}


def _connect_button(lang):
    return [{"action": "message", "label": CONNECT_BTN[lang], "messageText": CONNECT_MSG[lang]}]


def _connect_btn_if(linked, lang):
    """미연동 사용자에게만 '내 자료 연결' CTA 버튼을 붙인다(연동된 사용자는 빈 리스트)."""
    return [] if linked else _connect_button(lang)


def _welcome(lang):
    """첫 진입 대표 화면 — textCard(제목+설명+버튼) + 하단 메뉴 칩.

    basicCard 캐러셀은 카카오 규격상 thumbnail이 필수라 미발송 처리될 수 있어,
    이미지가 필요 없는 textCard로 첫 카드 내용을 보여준다. 버튼/문구는 동일.
    """
    title, desc, btns = WELCOME_CARDS[lang][0]
    buttons = [{"action": "message", "label": l, "messageText": m} for l, m in btns]
    card = {"textCard": {
        "title": (title or "")[:50],
        "description": (desc or "")[:400],
        "buttons": buttons[:3],
    }}
    return _card_response(card, lang, menu=True, with_disc=False)


def _link_help(lang):
    title, desc = LINK_HELP[lang]
    return _text_card(title, desc, lang, menu=True, disc=False)

LANG_PICK = ("언어를 선택하세요 / Chọn ngôn ngữ / Choose language")
LANG_BTNS = [("한국어", "한국어"), ("Tiếng Việt", "Tiếng Việt"), ("English", "English")]

FALLBACK = {
    "ko": "무엇을 도와드릴까요? 아래 버튼에서 골라보세요.\n'내 시급 확인'으로 내 시급이 최저임금보다 적은지 바로 확인할 수 있어요.",
    "vi": "Tôi có thể giúp gì? Hãy chọn nút bên dưới.\n'Kiểm tra lương' để xem lương giờ của bạn có dưới mức tối thiểu không.",
    "en": "How can I help? Pick a button below.\nTap 'Wage check' to see if your hourly pay is below minimum wage.",
}

# ── 증거 수집 가이드(언어별, 5종) ──
GUIDES = {
    "wage": {
        "ko": "💰 급여·임금 증거\n· 근로계약서 — 약속한 임금\n· 급여명세서 — 임금·공제 내역\n· 통장 입금내역 — 실제 받은 금액\n최근 3개월치를 모으면 좋아요.",
        "vi": "💰 Bằng chứng tiền lương\n· Hợp đồng — mức lương đã hứa\n· Bảng lương — lương & khấu trừ\n· Sao kê ngân hàng — số tiền thực nhận\nNên thu thập 3 tháng gần nhất.",
        "en": "💰 Wage evidence\n· Contract — promised pay\n· Payslip — pay & deductions\n· Bank record — actual amount received\nCollect the last 3 months.",
    },
    "time": {
        "ko": "⏰ 근무시간 증거\n· 출퇴근 기록(지문·카드·앱)\n· 근무표·스케줄\n· 직접 쓴 근무일지(날짜·시간)\n연장·야간·휴일은 따로 표시하세요.",
        "vi": "⏰ Bằng chứng giờ làm\n· Chấm công (vân tay·thẻ·app)\n· Bảng ca làm\n· Nhật ký tự ghi (ngày·giờ)\nGhi riêng giờ tăng ca·đêm·ngày lễ.",
        "en": "⏰ Working-hours evidence\n· Clock-in records (fingerprint·card·app)\n· Work schedule\n· Self-kept work log (date·time)\nMark overtime·night·holiday separately.",
    },
    "relation": {
        "ko": "📄 근로관계 증거\n· 근로계약서\n· 명함·사원증·근무복 사진\n· 업무 지시 카톡·문자\n· 사업장 상호·주소·사업자번호\n'직원 아니다'에 대비하세요.",
        "vi": "📄 Bằng chứng quan hệ lao động\n· Hợp đồng\n· Danh thiếp·thẻ NV·đồng phục\n· Tin nhắn giao việc\n· Tên·địa chỉ·MST nơi làm\nĐề phòng bị nói 'không phải nhân viên'.",
        "en": "📄 Employment-relation evidence\n· Contract\n· Business card·ID·uniform photo\n· Work-order messages\n· Workplace name·address·biz number\nGuard against 'not an employee' claims.",
    },
    "chat": {
        "ko": "💬 대화·정황 증거\n· 사장님과 임금 관련 카톡·문자·녹음\n· '다음에 줄게' 같은 지급 약속·지연\n· 동료 연락처\n내가 당사자인 녹음은 합법이에요.",
        "vi": "💬 Bằng chứng trao đổi\n· Tin nhắn·ghi âm với chủ về lương\n· Lời hứa/trì hoãn trả lương\n· Liên hệ đồng nghiệp\nGhi âm khi bạn là người trong cuộc là hợp pháp.",
        "en": "💬 Conversation evidence\n· Chats·recordings with employer about pay\n· Promises/delays like 'I'll pay later'\n· Coworker contacts\nRecording a talk you're part of is legal.",
    },
    "report": {
        "ko": "🏛️ 신고 방법\n임금을 못 받으면 고용노동부에 '임금체불 진정'을 넣을 수 있어요.\n· 온라인: labor.moel.go.kr\n· 방문: 관할 고용노동청\n· 무료, 본인이 직접 접수\n계약서·명세서·입금내역·근무기록을 먼저 정리하세요.",
        "vi": "🏛️ Cách khiếu nại\nNếu bị nợ lương, bạn có thể nộp đơn lên Bộ Lao động.\n· Online: labor.moel.go.kr\n· Trực tiếp: Văn phòng Lao động khu vực\n· Miễn phí, tự nộp\nChuẩn bị hợp đồng·bảng lương·sao kê·giờ làm trước.",
        "en": "🏛️ How to report\nIf unpaid, you can file a complaint with the Ministry of Employment & Labor.\n· Online: labor.moel.go.kr\n· In person: local Labor Office\n· Free, file it yourself\nPrepare contract·payslip·bank record·hours first.",
    },
}

GENERIC_TODO = {
    "ko": "✅ 오늘 모으면 좋은 증거\n1. 통장 입금내역 3개월\n2. 근로계약서\n3. 최근 급여명세서\n4. 이번 주 출퇴근 기록\n5. 사장님과의 임금 대화 캡처\n사진으로 찍어 BADA 앱에 올리면 자동 정리돼요.",
    "vi": "✅ Nên thu thập hôm nay\n1. Sao kê 3 tháng\n2. Hợp đồng lao động\n3. Bảng lương gần nhất\n4. Chấm công tuần này\n5. Ảnh tin nhắn về lương với chủ\nChụp ảnh tải lên app BADA để tự sắp xếp.",
    "en": "✅ Collect today\n1. 3-month bank record\n2. Employment contract\n3. Recent payslip\n4. This week's hours\n5. Pay-related chats with employer\nSnap photos to the BADA app for auto-sorting.",
}

# ── 진단 메시지(언어별, 동적) ──
def _t_diag_ask(lang):
    return {
        "ko": "내 시급이 최저임금보다 적은지 바로 확인해 드려요.\n시급을 알려주세요. 예: '시급 9000'",
        "vi": "Tôi sẽ kiểm tra lương giờ của bạn so với lương tối thiểu.\nHãy cho biết lương giờ. Ví dụ: 'lương 9000'",
        "en": "I'll check your hourly pay against minimum wage.\nTell me your hourly pay. e.g. 'wage 9000'",
    }[lang]


def _t_diag_below(lang, wage, floor, gap):
    month = gap * 209
    if lang == "vi":
        return (f"⚠️ Lương giờ {wage:,}원 thấp hơn lương tối thiểu năm nay ({floor:,}원) {gap:,}원.\n\n"
                f"Có thể dưới mức tối thiểu. Mỗi giờ chênh {gap:,}원, một tháng (≈209 giờ) khoảng {month:,}원.\n\n"
                "Hãy thu thập bảng lương·sao kê và tải lên app BADA để tính chính xác. "
                "Kết luận cuối cùng cần xác nhận tại Bộ Lao động·tổ chức tư vấn.")
    if lang == "en":
        return (f"⚠️ Hourly pay {wage:,}원 is {gap:,}원 below this year's minimum wage ({floor:,}원).\n\n"
                f"This may be below minimum. {gap:,}원 short per hour, about {month:,}원 per month (≈209h).\n\n"
                "Collect your payslip·bank record and upload to the BADA app for an exact calculation. "
                "Final judgment must be confirmed by the Labor Ministry·a counseling center.")
    return (f"⚠️ 시급 {wage:,}원은 올해 최저임금 {floor:,}원보다 {gap:,}원 낮아요.\n\n"
            f"최저임금 미달일 수 있어요. 한 시간에 {gap:,}원씩, 한 달(약 209시간)이면 약 {month:,}원 차이가 날 수 있어요.\n\n"
            "급여명세서·입금내역을 모아 BADA 앱에 올리면 정확히 계산해 드려요. 확정 판단은 고용노동부·상담기관에서 확인하세요.")


def _t_diag_ok(lang, wage, floor):
    if lang == "vi":
        return (f"Lương giờ {wage:,}원 đạt hoặc trên lương tối thiểu năm nay ({floor:,}원). 👍\n\n"
                "Tuy nhiên phụ cấp ngày nghỉ·tăng ca hoặc khấu trừ quá mức vẫn cần kiểm tra riêng. "
                "Tải bảng lương lên để kiểm tra các mục đó.")
    if lang == "en":
        return (f"Hourly pay {wage:,}원 meets or exceeds this year's minimum wage ({floor:,}원). 👍\n\n"
                "But weekly-holiday·overtime allowances or excessive deductions still need a separate check. "
                "Upload your payslip to check those.")
    return (f"시급 {wage:,}원은 올해 최저임금 {floor:,}원 이상이에요. 👍\n\n"
            "다만 주휴수당·연장/야간수당 누락, 과다공제는 따로 확인이 필요할 수 있어요. 급여명세서를 올리면 그런 항목까지 점검해 드려요.")


# ── 응답 빌더 ──
def _template(text: str, lang: str = "ko", menu: bool = True, disc: bool = False) -> dict[str, Any]:
    text = (text or "").strip()
    if disc:
        dis = DISCLAIMER[lang]
        if dis not in text:
            text = f"{text}\n\n{dis}"
    if len(text) > _MAX_TEXT:
        text = text[: _MAX_TEXT - 1].rstrip() + "…"
    btns = LANG_BTNS if not menu else MENU[lang]
    quick = [{"action": "message", "label": l, "messageText": m} for l, m in btns]
    return {"version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": text}}], "quickReplies": quick}}


def _won(n: Any) -> str:
    try:
        return f"{int(n):,}원"
    except (TypeError, ValueError):
        return "?"


# ── 언어 감지 ──
_VI_CHARS = "ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ"


def _detect_lang(u: str) -> str:
    s = u.lower().strip()
    if s in ("tiếng việt", "tieng viet", "vietnam", "vi"):
        return "vi"
    if s in ("english", "en"):
        return "en"
    if "한국어" in u or s in ("korean", "ko"):
        return "ko"
    if re.search(r"[가-힣]", u):
        return "ko"
    if re.search(f"[{_VI_CHARS}]", u.lower()):
        return "vi"
    if re.fullmatch(r"[A-Za-z0-9]{6}", s) and re.search(r"[0-9]", s):  # 코드(영문+숫자)만 → 기본 한국어
        return "ko"
    if re.search(r"[a-zA-Z]", u):
        return "en"
    return "ko"


# ── 의도 감지(다국어 키워드) ──
INTENT_KW = {
    "menu": ["처음으로", "처음", "시작하기", "시작", "메뉴", "menu", "start", "home", "bắt đầu", "bat dau", "trang chủ"],
    "language": ["language", "언어", "tiếng việt", "tieng viet", "한국어", "english"],
    "link": ["연동", "연결", "코드", "link", "connect", "kết nối", "ket noi", "mã", "code"],
    "diagnose": ["진단", "최저임금", "시급", "내시급", "wage", "minimum", "lương", "luong", "kiểm tra lương", "salary"],
    "checklist": ["체크리스트", "체크", "준비상태", "준비 상태", "checklist", "readiness",
                  "danh sách kiểm tra", "danh sach", "tình trạng", "chuẩn bị", "진행률"],
    "status": ["내사건", "사건현황", "현황", "mycase", "case", "hồ sơ", "ho so", "상태", "미지급", "체불액"],
    "missing": ["부족", "필요한자료", "누락", "missing", "còn thiếu", "con thieu"],
    "todo": ["오늘", "할일", "today", "hôm nay", "hom nay", "việc hôm nay", "tasks"],
    "wage": ["급여", "임금", "월급", "명세서", "입금", "payslip", "bảng lương", "tiền lương"],
    "time": ["근무시간", "출퇴근", "야간", "연장", "휴일", "근무표", "hours", "schedule", "giờ làm", "chấm công"],
    "relation": ["근로관계", "계약", "사업자", "고용", "사장", "contract", "employer", "hợp đồng", "hop dong"],
    "chat": ["대화", "정황", "카톡", "문자", "녹음", "약속", "chat", "recording", "tin nhắn", "ghi âm"],
    "report": ["신고", "절차", "진정", "노동청", "고용노동부", "report", "complaint", "khiếu nại", "khieu nai"],
}


def _intent(u: str) -> str | None:
    s = u.lower()
    for name, kws in INTENT_KW.items():
        if any(k.replace(" ", "").lower() in s for k in kws):
            return name
    return None


# ── DB: 연동 사용자 또는 최근 사건 ──
def _resolve_user_id(db, kakao_user_id: str | None) -> str | None:
    """연동돼 있으면 그 BADA user_id 반환(없으면 None)."""
    if not kakao_user_id:
        return None
    try:
        from ..models import KakaoLink
        link = db.query(KakaoLink).filter(KakaoLink.kakao_user_id == kakao_user_id).first()
        return link.user_id if link else None
    except Exception:
        return None


def _is_linked(kakao_user_id: str | None) -> bool:
    """카카오 사용자가 BADA 계정과 연동돼 있는지."""
    db = SessionLocal()
    try:
        return _resolve_user_id(db, kakao_user_id) is not None
    finally:
        db.close()


def _load_case(kakao_user_id: str | None) -> dict[str, Any] | None:
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db, kakao_user_id)
        if not uid:
            return None  # 미연동: 남의 사건이 보이지 않도록 임의 사건 조회 금지
        case = (db.query(Case).filter(Case.user_id == uid)
                .order_by(Case.created_at.desc()).first())
        if not case:
            return None
        analysis = (db.query(AnalysisResult).filter(AnalysisResult.case_id == case.id)
                    .order_by(AnalysisResult.created_at.desc()).first())
        evidences = db.query(Evidence).filter(Evidence.case_id == case.id).all()
        codes = []
        for e in evidences:
            if e.category not in codes:
                codes.append(e.category)
        return {
            "linked": bool(uid),
            "workplace": case.workplace_name or "",
            "hourly_wage": case.agreed_hourly_wage,
            "evidence_count": len(evidences),
            "category_codes": codes,
            "suspected_unpaid": getattr(analysis, "suspected_unpaid", None) if analysis else None,
            "missing": (getattr(analysis, "missing_evidences", None) if analysis else None) or [],
            "has_analysis": analysis is not None,
        }
    except Exception:
        return None
    finally:
        db.close()


def _try_link(kakao_user_id: str | None, utterance: str, lang: str) -> str | None:
    """발화에 연동코드가 있으면 매핑. 성공/실패 메시지 반환, 코드 없으면 None."""
    s = utterance.strip().upper()
    code = None
    if re.fullmatch(r"[A-Z0-9]{6}", s) and any(ch.isdigit() for ch in s):
        code = s
    else:
        m = re.search(r"\b([A-Z0-9]{6})\b", s)
        if m and any(ch.isdigit() for ch in m.group(1)):
            code = m.group(1)
    if not code or not kakao_user_id:
        return None
    db = SessionLocal()
    try:
        from ..models import KakaoLink, KakaoLinkCode
        rec = db.query(KakaoLinkCode).filter(KakaoLinkCode.code == code, KakaoLinkCode.used == False).first()  # noqa: E712
        if not rec:
            return {"ko": "연동 코드가 올바르지 않거나 만료됐어요. 앱에서 새 코드를 받아주세요.",
                    "vi": "Mã kết nối không đúng hoặc đã hết hạn. Hãy lấy mã mới trong app.",
                    "en": "The link code is invalid or expired. Get a new code in the app."}[lang]
        link = db.query(KakaoLink).filter(KakaoLink.kakao_user_id == kakao_user_id).first()
        if link:
            link.user_id = rec.user_id
        else:
            db.add(KakaoLink(kakao_user_id=kakao_user_id, user_id=rec.user_id))
        rec.used = True
        db.commit()
        return {"ko": "✅ 계정이 연동됐어요! 이제 '내 사건 현황'을 누르면 내 자료 기준으로 안내해 드려요.",
                "vi": "✅ Đã kết nối tài khoản! Bấm 'Hồ sơ của tôi' để xem theo tài liệu của bạn.",
                "en": "✅ Account linked! Tap 'My case' to see info based on your own files."}[lang]
    except Exception:
        return None
    finally:
        db.close()


# ── 텍스트 빌더(언어별 동적) ──
def _missing_items(c, lang):
    """analysis.missing_evidences가 dict({'item','reason'})·문자열 어떤 형태여도 (라벨, 사유)로 정규화."""
    out = []
    for m in ((c.get("missing") if c else None) or []):
        if isinstance(m, dict):
            item = m.get("item") or m.get("category") or ""
            reason = (m.get("reason") or "").strip()
            label = CATEGORY[lang].get(item, item) if item else reason
            if item and label == item and not CATEGORY[lang].get(item):
                label = reason or item  # 알 수 없는 코드면 사유로 대체
        else:
            label = CATEGORY[lang].get(str(m), str(m))
            reason = ""
        label = (label or "").strip()
        if label and label not in [x[0] for x in out]:
            out.append((label, reason))
    return out


def _missing_join(c, lang):
    return ", ".join(l for l, _ in _missing_items(c, lang))


def _status_text(c, lang):
    cat = CATEGORY[lang]
    cats = ", ".join(cat.get(x, x) for x in c["category_codes"])
    if lang == "vi":
        L = [f"📁 Hồ sơ {c['workplace'] or 'của tôi'}", ""]
        if c["has_analysis"] and c["suspected_unpaid"] is not None:
            L.append(f"· Nghi ngờ chưa trả: {_won(c['suspected_unpaid'])} (chưa xác định, cần xác nhận)")
        L.append(f"· Tài liệu đã tải: {c['evidence_count']}" + (f" ({cats})" if cats else ""))
        L.append(f"· Còn cần: {_missing_join(c, lang)}" if c["missing"] else "· Tài liệu cơ bản đã đủ.")
        L += ["", "Xem phân tích chi tiết trong app BADA."]
        return "\n".join(L)
    if lang == "en":
        L = [f"📁 {c['workplace'] or 'My'} case", ""]
        if c["has_analysis"] and c["suspected_unpaid"] is not None:
            L.append(f"· Suspected unpaid: {_won(c['suspected_unpaid'])} (not confirmed, needs review)")
        L.append(f"· Uploaded files: {c['evidence_count']}" + (f" ({cats})" if cats else ""))
        L.append(f"· Still needed: {_missing_join(c, lang)}" if c["missing"] else "· Basic files are ready.")
        L += ["", "See full analysis in the BADA app."]
        return "\n".join(L)
    L = [f"📁 {c['workplace'] or '내'} 사건 현황", ""]
    if c["has_analysis"] and c["suspected_unpaid"] is not None:
        L.append(f"· 의심 미지급액: {_won(c['suspected_unpaid'])} (확정 아님, 상담기관 확인 필요)")
    L.append(f"· 업로드한 자료: {c['evidence_count']}건" + (f" ({cats})" if cats else ""))
    L.append(f"· 더 필요한 자료: {_missing_join(c, lang)}" if c["missing"] else "· 기본 자료는 갖춰졌어요.")
    L += ["", "자세한 분석·Evidence Pack은 BADA 앱에서 확인하세요."]
    return "\n".join(L)


def _no_case(lang):
    return {"ko": "아직 BADA 앱에 등록된 사건이 없어요. 앱에서 서류를 올리고 분석하면 여기서 현황을 알려드릴게요.",
            "vi": "Chưa có hồ sơ nào trong app BADA. Hãy tải tài liệu và phân tích trong app.",
            "en": "No case in the BADA app yet. Upload files and analyze in the app first."}[lang]


def _checklist_text(c, lang):
    have = set(c.get("category_codes", [])) if c else set()
    cat = CATEGORY[lang]
    done = sum(1 for x in _REQUIRED if x in have)
    title = {"ko": f"📋 증거 체크리스트 ({done}/{len(_REQUIRED)} 완료)",
             "vi": f"📋 Danh sách bằng chứng ({done}/{len(_REQUIRED)} xong)",
             "en": f"📋 Evidence checklist ({done}/{len(_REQUIRED)} done)"}[lang]
    lines = [title, ""]
    for x in _REQUIRED:
        lines.append(("✅ " if x in have else "⬜ ") + cat.get(x, x))
    lines.append("")
    if done == len(_REQUIRED):
        lines.append({"ko": "기본 자료가 다 모였어요! 상담·신고 준비가 거의 끝났어요.",
                      "vi": "Đã đủ tài liệu cơ bản! Gần sẵn sàng để khiếu nại.",
                      "en": "All basic files collected! Almost ready to file."}[lang])
    elif c:
        lines.append({"ko": "없는 자료를 사진으로 BADA 앱에 올리면 진행률이 채워져요.",
                      "vi": "Tải tài liệu còn thiếu lên app BADA để tăng tiến độ.",
                      "en": "Upload missing files to the BADA app to fill progress."}[lang])
    else:
        lines.append({"ko": "BADA 앱에서 사건을 만들고 자료를 올리면 진행률이 채워져요.",
                      "vi": "Tạo hồ sơ và tải tài liệu trong app BADA để bắt đầu.",
                      "en": "Create a case and upload files in the BADA app to begin."}[lang])
    return "\n".join(lines)


def _missing_text(c, lang):
    if c and c["missing"]:
        rows = _missing_items(c, lang)
        items = "\n".join(
            (f"· {label}" + (f" — {reason}" if (reason and lang == "ko") else ""))
            for label, reason in rows
        )
        head = {"ko": "🔎 더 모으면 좋은 자료\n\n", "vi": "🔎 Nên bổ sung\n\n", "en": "🔎 Worth adding\n\n"}[lang]
        tail = {"ko": "\n\n사진으로 찍어 BADA 앱에 올리면 분석이 더 정확해져요.",
                "vi": "\n\nChụp ảnh tải lên app BADA để phân tích chính xác hơn.",
                "en": "\n\nSnap photos to the BADA app for more accurate analysis."}[lang]
        return head + items + tail
    return {"ko": "현재 사건 기준으로 뚜렷한 누락 자료는 없어요. 원본 서류를 한 번 더 점검해 두세요.",
            "vi": "Hiện không thấy thiếu rõ ràng. Hãy kiểm tra lại bản gốc.",
            "en": "No clear missing files right now. Double-check your originals."}[lang]


def _todo_text(c, lang):
    if c and c["missing"]:
        items = "\n".join(f"{i+1}. {label}" for i, (label, _) in enumerate(_missing_items(c, lang)))
        head = {"ko": "✅ 오늘 모으면 좋은 자료 (내 사건 기준)\n\n",
                "vi": "✅ Nên thu thập hôm nay (theo hồ sơ)\n\n",
                "en": "✅ Collect today (for your case)\n\n"}[lang]
        return head + items
    return GENERIC_TODO[lang]


def _parse_wage(u: str):
    for m in re.findall(r"[\d,]{3,}", u):
        try:
            v = int(m.replace(",", ""))
        except ValueError:
            continue
        if 3000 <= v <= 100000:
            return v
    return None


def _diagnose_text(utterance, c, lang):
    wage = _parse_wage(utterance) or (c.get("hourly_wage") if c else None)
    if not wage:
        return _t_diag_ask(lang)
    try:
        from rules.legal import check_minimum_wage, min_hourly_wage
    except Exception:
        return _t_diag_ask(lang)
    floor = min_hourly_wage()
    res = check_minimum_wage(wage)
    if res:
        return _t_diag_below(lang, wage, floor, res["shortfall_per_hour"])
    return _t_diag_ok(lang, wage, floor)


# ── 리치 카드 응답 빌더 (시각·구조·상호작용 개선) ──
def _app_button(lang):
    """BADA_APP_URL 환경변수가 있을 때만 '앱 열기' webLink 버튼 (배포 후 채우면 자동 활성)."""
    url = (os.environ.get("BADA_APP_URL") or "").strip()
    if not url:
        return []
    label = {"ko": "BADA 앱 열기", "vi": "Mở app BADA", "en": "Open BADA app"}[lang]
    return [{"action": "webLink", "label": label, "webLinkUrl": url}]


def _quick(lang, menu=True):
    btns = LANG_BTNS if not menu else MENU[lang]
    return [{"action": "message", "label": l, "messageText": m} for l, m in btns]


def _card_response(card, lang, menu=True, with_disc=False):
    outputs = [card]
    if with_disc:
        outputs.append({"simpleText": {"text": DISCLAIMER[lang]}})
    return {"version": "2.0", "template": {"outputs": outputs, "quickReplies": _quick(lang, menu)}}


def _text_card(title, desc, lang, buttons=None, menu=True, disc=False):
    title = (title or "").strip()[:50]
    desc = (desc or "").strip()
    if len(desc) > 400:
        desc = desc[:399].rstrip() + "…"
    card = {"textCard": {"title": title, "description": desc}}
    btns = (buttons or []) + _app_button(lang)
    if btns:
        card["textCard"]["buttons"] = btns[:3]
    return _card_response(card, lang, menu=menu, with_disc=disc)


def _split_card(text, lang, menu=True, buttons=None, disc=False):
    """'헤더\\n본문' 텍스트 → textCard(제목+설명). 단문이면 simpleText 그대로."""
    text = (text or "").strip()
    head, _, body = text.partition("\n")
    body = body.strip()
    if not body:
        return _template(text, lang, menu, disc=disc)
    return _text_card(head, body, lang, buttons=buttons, menu=menu, disc=disc)


_CHK_DESC = {
    "ko": {"contract": "임금·공제 조건", "statement": "지급액·공제 항목", "payment": "실제 입금 내역", "schedule": "근무시간 기록"},
    "vi": {"contract": "Điều kiện lương·trừ", "statement": "Số tiền·khoản trừ", "payment": "Tiền vào thực tế", "schedule": "Giờ làm việc"},
    "en": {"contract": "Wage·deduction terms", "statement": "Amount·deductions", "payment": "Actual deposits", "schedule": "Work hours"},
}


def _checklist_card(c, lang):
    have = set(c.get("category_codes", [])) if c else set()
    cat = CATEGORY[lang]
    done = sum(1 for x in _REQUIRED if x in have)
    header = {"ko": f"📋 체크리스트 {done}/{len(_REQUIRED)}",
              "vi": f"📋 Checklist {done}/{len(_REQUIRED)}",
              "en": f"📋 Checklist {done}/{len(_REQUIRED)}"}[lang]
    items = []
    for x in _REQUIRED:
        mark = "✅ " if x in have else "⬜ "
        items.append({"title": (mark + cat.get(x, x))[:36], "description": _CHK_DESC[lang].get(x, "")[:40]})
    card = {"listCard": {"header": {"title": header}, "items": items}}
    btns = _app_button(lang)
    if btns:
        card["listCard"]["buttons"] = btns[:3]
    return _card_response(card, lang, menu=True, with_disc=False)


# ── 연동 게이트(미연동 사용자가 '내 자료' 기능 진입 시) ──
_GATE = {
    "status": {
        "ko": ("🔗 연결이 필요해요",
               "내 사건 현황은 내가 올린 자료를 봐야 해서 연결이 필요해요.\n\n"
               "BADA 앱에서 로그인 → '카카오 연동'에서 6자리 코드를 받아, 여기에 붙여넣어 주세요. 연결은 한 번만 하면 돼요."),
        "vi": ("🔗 Cần kết nối",
               "Hồ sơ của tôi cần xem tài liệu bạn đã tải lên nên phải kết nối.\n\n"
               "Trong app BADA, đăng nhập → 'Kết nối Kakao' để lấy mã 6 ký tự, rồi dán vào đây. Chỉ cần kết nối một lần."),
        "en": ("🔗 Connection needed",
               "My case reads the files you uploaded, so it needs a connection.\n\n"
               "In the BADA app, log in → 'Kakao link' to get a 6-character code, then paste it here. You only connect once."),
    },
    "checklist": {
        "ko": ("📋 준비 상태 체크",
               "임금체불 신고엔 보통 이 자료가 필요해요:\n· 근로계약서\n· 급여명세서\n· 입금내역\n· 근무표\n\n"
               "내가 뭘 갖췄는지 자동으로 보려면 연결하세요. 앱에서 6자리 코드를 받아 여기에 붙여넣으면 돼요."),
        "vi": ("📋 Tình trạng chuẩn bị",
               "Để khiếu nại nợ lương thường cần:\n· Hợp đồng lao động\n· Bảng lương\n· Sao kê chuyển khoản\n· Bảng chấm công\n\n"
               "Muốn tự động xem bạn đã có gì, hãy kết nối. Lấy mã 6 ký tự trong app rồi dán vào đây."),
        "en": ("📋 Readiness check",
               "Filing for unpaid wages usually needs:\n· Employment contract\n· Payslip\n· Bank transfer record\n· Work schedule\n\n"
               "To see what you already have automatically, connect. Get a 6-character code in the app and paste it here."),
    },
}


def _gate_button(lang):
    label = {"ko": "연결 방법", "vi": "Cách kết nối", "en": "How to connect"}[lang]
    msg = {"ko": "연동", "vi": "kết nối", "en": "connect"}[lang]
    return [{"action": "message", "label": label, "messageText": msg}]


def _link_gate(feature, lang):
    title, desc = _GATE[feature][lang]
    return _text_card(title, desc, lang, buttons=_gate_button(lang), menu=True, disc=False)


def _diagnose_response(utterance, case, lang, linked=True):
    """시급 진단 카드 + '준비 상태 체크' 브릿지 버튼(+미연동이면 '내 자료 연결') + 고지문구."""
    bl = {"ko": "준비 상태 체크", "vi": "Tình trạng chuẩn bị", "en": "Readiness check"}[lang]
    bridge = [{"action": "message", "label": bl, "messageText": bl}] + _connect_btn_if(linked, lang)
    return _split_card(_diagnose_text(utterance, case, lang), lang, buttons=bridge, disc=True)


# ── 핸들러 ──
@router.post("/skill")
async def kakao_skill(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}
    ureq = (body or {}).get("userRequest", {}) or {}
    utterance = (ureq.get("utterance", "") or "").strip()
    kakao_user_id = ((ureq.get("user") or {}).get("id"))
    lang = _detect_lang(utterance)

    if not utterance:
        return _welcome(lang)

    u = utterance.replace(" ", "")
    intent = _intent(u)

    # 처음으로/시작하기/메뉴 → 웰컴 카드 재노출(기존 사용자도 ≡ 메뉴에서 다시 볼 수 있게)
    if intent == "menu":
        return _welcome(lang)

    # 언어 선택
    if intent == "language" or utterance in ("한국어", "Tiếng Việt", "English"):
        if utterance in ("한국어", "Tiếng Việt", "English"):
            return _welcome(lang)
        return _template(LANG_PICK, lang, menu=False)

    # 계정 연동(코드 입력)
    if intent == "link":
        msg = _try_link(kakao_user_id, utterance, lang)
        if msg:
            return _template(msg, lang)
        return _link_help(lang)

    # 코드만 덜렁 보낸 경우도 연동 시도
    linkmsg = _try_link(kakao_user_id, utterance, lang)
    if linkmsg:
        return _template(linkmsg, lang)

    linked = _is_linked(kakao_user_id)
    case = _load_case(kakao_user_id)  # 연동된 경우에만 본인 사건(아니면 None)

    # 내 시급 확인 — 연동 없이도 동작. 결과에 '준비 상태 체크' 브릿지 + 고지문구.
    if intent == "diagnose":
        return _diagnose_response(utterance, case, lang, linked)

    # 준비 상태 체크 — 내 자료 필요. 미연동이면 게이트.
    if intent == "checklist":
        return _checklist_card(case, lang) if linked else _link_gate("checklist", lang)

    # 내 사건 현황 — 내 자료 필요. 미연동이면 게이트.
    if intent == "status":
        if not linked:
            return _link_gate("status", lang)
        return _split_card(_status_text(case, lang), lang, disc=True) if case else _template(_no_case(lang), lang)

    # 더 필요한 자료 — 개인 분석. 미연동이면 게이트.
    if intent == "missing":
        return _split_card(_missing_text(case, lang), lang) if linked else _link_gate("checklist", lang)

    # 오늘 할 일 — 연동 시 내 사건 기준, 아니면 일반 권장(누구나).
    if intent == "todo":
        return _split_card(_todo_text(case, lang), lang, buttons=_connect_btn_if(linked, lang))

    # 가이드(급여·시간·관계·대화·신고). 신고만 고지문구.
    if intent in GUIDES:
        return _split_card(GUIDES[intent][lang], lang, disc=(intent == "report"),
                           buttons=_connect_btn_if(linked, lang))

    # 숫자만 보낸 경우(예: "9000") → 시급 진단으로 (안내 못 읽고 숫자만 치는 사용자 배려)
    if intent is None and _parse_wage(utterance):
        return _diagnose_response(utterance, case, lang, linked)

    return _split_card(FALLBACK[lang], lang, buttons=_connect_btn_if(linked, lang))
