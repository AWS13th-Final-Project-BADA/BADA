"""카카오 i 오픈빌더 스킬 서버 - BADA 증거 수집 가이드 + 내 사건 현황.

두 가지를 한다:
1) 일반 가이드(증거 수집 체크리스트) — DB 없이 항상 즉시 응답.
2) 내 사건 현황 — 실제 BADA DB(Case·AnalysisResult·Evidence)를 읽어 맞춤 안내.
   (데모: 사용자 구분은 아직 없어 '가장 최근 사건'을 읽음. 로그인 도입 시 사용자별로 확장.)

- LLM 미사용 → 항상 5초 안에 응답(카카오 제한 안전).
- 법적 판단/대리/강권 안 함. 준비 보조 + 정보 제공만(법률자문 아님).
"""
from typing import Any

from fastapi import APIRouter, Request

from ..db import SessionLocal
from ..models import AnalysisResult, Case, Evidence

router = APIRouter(prefix="/kakao", tags=["kakao"])

_MAX_TEXT = 950
_DISCLAIMER = "※ 일반 정보 안내이며 법률자문이 아닙니다."

# 증거 카테고리 코드 → 한국어 라벨.
_CATEGORY_KO = {
    "contract": "근로계약서",
    "schedule": "근무표",
    "payment": "입금내역",
    "chat": "대화 캡처",
    "statement": "급여명세서",
    "other": "기타 자료",
}

# 메뉴(빠른 답변) — label은 14자 이내.
_MENU = [
    ("내 사건 현황", "내 사건 현황"),
    ("오늘 할 일", "오늘 할 일"),
    ("부족한 자료", "부족한 자료"),
    ("급여·임금 증거", "급여 임금 증거"),
    ("근무시간 증거", "근무시간 증거"),
    ("신고 절차", "신고 절차"),
]

_WELCOME = (
    "안녕하세요, BADA예요 🌊\n"
    "임금체불 대비 증거 수집을 도와드려요.\n\n"
    "· '내 사건 현황' — BADA 앱에 올린 내 자료 기준 현황\n"
    "· '오늘 할 일' — 지금 모으면 좋은 증거\n"
    "아래 버튼을 눌러보세요. 자료는 사진으로 찍어 BADA 앱에 올리면 자동 정리돼요."
)

# 일반 가이드 (사건 데이터 없이) — (키워드들, 안내문).
_TOPICS: list[tuple[list[str], str]] = [
    (
        ["급여", "임금", "월급", "명세서", "입금", "돈", "얼마", "최저임금"],
        "💰 급여·임금 증거 (얼마를 못 받았는지)\n\n"
        "· 근로계약서·연봉계약서 — 약속한 임금\n"
        "· 급여명세서 — 명시된 임금과 공제 내역\n"
        "· 통장 입금내역 — 실제 받은 금액(은행 앱 거래내역 캡처)\n"
        "· 최근 3개월치 입금내역을 함께 모아두면 좋아요\n\n"
        "'계약서 → 급여명세서 → 입금내역'을 한 세트로 준비하면 차이를 보여주기 쉬워요.",
    ),
    (
        ["근무시간", "출퇴근", "야간", "연장", "휴일", "근무표", "스케줄"],
        "⏰ 근무시간 증거 (얼마나 일했는지)\n\n"
        "· 출퇴근 기록 — 지문·카드·출퇴근 앱 캡처\n"
        "· 근무표·스케줄표 사진\n"
        "· 직접 쓴 근무일지 — 날짜·출퇴근 시간을 매일 적어두면 그 자체로 증거가 돼요\n"
        "· 연장·야간·휴일근로는 시간을 따로 표시\n\n"
        "기록이 없다면 지금부터라도 매일 적어두세요.",
    ),
    (
        ["근로관계", "계약", "사원증", "명함", "사업자", "고용", "사장"],
        "📄 근로관계 증거 (누구 밑에서 일했는지)\n\n"
        "· 근로계약서\n· 명함·사원증·근무복 사진\n· 업무 지시 카톡·문자\n"
        "· 사업장 상호·주소·사업자등록번호\n\n"
        "'직원이 아니다'라는 주장에 대비해, 그곳에서 실제로 일했다는 자료를 모아두세요.",
    ),
    (
        ["대화", "정황", "카톡", "문자", "녹음", "약속", "동료", "증인"],
        "💬 대화·정황 증거\n\n"
        "· 사장님과 임금 관련 대화 — 카톡·문자 캡처, 통화 녹음\n"
        "· '다음에 줄게' 같은 지급 약속·지연 메시지\n· 함께 일한 동료의 연락처\n\n"
        "내가 대화 당사자인 녹음은 합법이에요. 임금을 언제 주기로 했는지 드러나는 메시지가 특히 중요해요.",
    ),
    (
        ["신고", "절차", "진정", "노동청", "고용노동부", "어디"],
        "🏛️ 신고는 어떻게 하나요?\n\n"
        "임금을 못 받았다면 고용노동부에 '임금체불 진정'을 넣을 수 있어요.\n"
        "· 온라인: 고용노동부 노동포털(labor.moel.go.kr)\n"
        "· 방문: 사업장 관할 고용노동청\n· 무료이며 본인이 직접 접수해요\n\n"
        "접수 전에 계약서·급여명세서·입금내역·근무기록을 정리해 두면 훨씬 수월해요. 구체적 판단은 고용노동부·상담기관에서 확인하세요.",
    ),
]

_GENERIC_TODO = (
    "✅ 오늘 모으면 좋은 증거\n\n"
    "1. 통장 입금내역 최근 3개월 캡처\n2. 근로계약서 사진\n3. 최근 급여명세서\n"
    "4. 이번 주 출퇴근 시간 기록\n5. 사장님과의 임금 관련 카톡·문자 캡처\n\n"
    "하나씩 사진으로 찍어 BADA 앱에 올리면 자동으로 정리돼요."
)


# ── 응답 빌더 ──
def _template(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if _DISCLAIMER not in text:
        text = f"{text}\n\n{_DISCLAIMER}"
    if len(text) > _MAX_TEXT:
        text = text[: _MAX_TEXT - 1].rstrip() + "…"
    quick = [{"action": "message", "label": l, "messageText": m} for l, m in _MENU]
    return {"version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": text}}], "quickReplies": quick}}


def _won(n: Any) -> str:
    try:
        return f"{int(n):,}원"
    except (TypeError, ValueError):
        return "확인 필요"


# ── DB: 최근 사건 읽기 (데모: 사용자 구분 전) ──
def _load_recent_case() -> dict[str, Any] | None:
    db = SessionLocal()
    try:
        case = db.query(Case).order_by(Case.created_at.desc()).first()
        if not case:
            return None
        analysis = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.case_id == case.id)
            .order_by(AnalysisResult.created_at.desc())
            .first()
        )
        evidences = db.query(Evidence).filter(Evidence.case_id == case.id).all()
        cats: list[str] = []
        for e in evidences:
            label = _CATEGORY_KO.get(e.category, e.category)
            if label not in cats:
                cats.append(label)
        return {
            "workplace": case.workplace_name or "내 사업장",
            "status": case.status,
            "evidence_count": len(evidences),
            "categories": cats,
            "suspected_unpaid": getattr(analysis, "suspected_unpaid", None) if analysis else None,
            "missing": (getattr(analysis, "missing_evidences", None) if analysis else None) or [],
            "has_analysis": analysis is not None,
        }
    except Exception:
        return None
    finally:
        db.close()


def _status_text(c: dict[str, Any]) -> str:
    lines = [f"📁 {c['workplace']} 사건 현황", ""]
    if c["has_analysis"] and c["suspected_unpaid"] is not None:
        lines.append(f"· 의심 미지급액: {_won(c['suspected_unpaid'])} (확정 아님, 상담기관 확인 필요)")
    lines.append(f"· 업로드한 자료: {c['evidence_count']}건"
                 + (f" ({', '.join(c['categories'])})" if c["categories"] else ""))
    if c["missing"]:
        lines.append(f"· 더 필요한 자료: {', '.join(str(m) for m in c['missing'])}")
    else:
        lines.append("· 기본 자료는 갖춰졌어요. 누락분은 상담 전 한 번 더 점검하세요.")
    lines.append("")
    lines.append("자세한 분석·Evidence Pack은 BADA 앱에서 확인하세요.")
    return "\n".join(lines)


def _missing_text(c: dict[str, Any]) -> str:
    if c["missing"]:
        items = "\n".join(f"· {m}" for m in c["missing"])
        return ("🔎 더 모으면 좋은 자료\n\n" + items
                + "\n\n이 자료들을 사진으로 찍어 BADA 앱에 올리면 분석이 더 정확해져요.")
    return ("현재 사건 기준으로 뚜렷한 누락 자료는 보이지 않아요. "
            "상담 전에 계약서·급여명세서·입금내역·근무기록 원본을 한 번 더 점검해 두세요.")


def _personal_todo_text(c: dict[str, Any]) -> str:
    if c["missing"]:
        items = "\n".join(f"{i+1}. {m}" for i, m in enumerate(c["missing"]))
        return ("✅ 오늘 모으면 좋은 자료 (내 사건 기준)\n\n" + items
                + "\n\n하나씩 BADA 앱에 올리면 자동으로 정리돼요.")
    return _GENERIC_TODO


# ── 라우팅 ──
def _is_status(u: str) -> bool:
    return any(k in u for k in ["내사건", "사건현황", "현황", "내거", "상태", "얼마남", "얼마못", "미지급", "체불액"])


def _is_missing(u: str) -> bool:
    return any(k in u for k in ["부족", "필요한자료", "뭐가부족", "뭐더", "누락"])


def _is_todo(u: str) -> bool:
    return any(k in u for k in ["오늘", "할일", "뭐부터", "무엇부터", "시작", "체크"])


def _match_generic(u: str) -> str:
    for keywords, body in _TOPICS:
        if any(k in u for k in keywords):
            return body
    return ""


@router.post("/skill")
async def kakao_skill(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}
    utterance = (((body or {}).get("userRequest", {}) or {}).get("utterance", "") or "").strip()
    if not utterance:
        return _template(_WELCOME)

    u = utterance.replace(" ", "")
    case = _load_recent_case()  # 데모: 최근 사건

    # 1) 사건 데이터가 필요한 의도 → 있으면 맞춤, 없으면 일반으로 폴백.
    if _is_status(u):
        return _template(_status_text(case) if case else
                         "아직 BADA 앱에 등록된 사건이 없어요. 앱에서 서류를 올리고 분석하면 여기서 현황을 알려드릴게요.")
    if _is_missing(u):
        if case:
            return _template(_missing_text(case))
    if _is_todo(u):
        return _template(_personal_todo_text(case) if case else _GENERIC_TODO)

    # 2) 일반 가이드 키워드.
    generic = _match_generic(u)
    if generic:
        return _template(generic)

    # 3) 미매칭 → 메뉴 유도.
    return _template(
        "증거 수집을 도와드려요. 아래 버튼에서 골라보세요.\n"
        "'내 사건 현황'을 누르면 BADA 앱에 올린 자료 기준으로 안내해 드려요."
    )
