"""카테고리 키워드 사전 — 분류 교차검증용(규칙 기반, LLM 금지).

용도: classify(이미지 형태 기반)가 내놓은 category를, OCR로 읽은 실제 텍스트의
키워드와 대조해 "형태 판단"과 "내용"이 일치하는지 검증한다.

원칙(architecture.md): 판단·생성 금지. 단어 매칭 점수만 낸다. 설명 가능해야 한다.
"""
from __future__ import annotations

# 카테고리별 "이 단어가 보이면 그 카테고리일 가능성이 높다" 사전
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "contract": [
        "근로계약", "계약서", "연봉계약", "갑", "을", "서명", "날인",
        "근로조건", "계약기간", "수습", "근무장소", "담당업무",
    ],
    "statement": [
        "급여명세", "임금명세", "지급액", "공제", "공제액", "실수령",
        "기본급", "수당", "상여", "세전", "세후", "지급총액", "공제총액",
    ],
    "payment": [
        "입금", "출금", "잔액", "거래내역", "이체", "예금", "통장",
        "은행", "계좌", "거래일시", "적요",
    ],
    "schedule": [
        "근무표", "출퇴근", "출근", "퇴근", "근무시간", "스케줄",
        "근태", "교대", "shift", "근무일",
    ],
    "chat": [
        "님", "ㅋㅋ", "ㅎㅎ", "보냈습니다", "읽음", "오전", "오후",
        "수고", "내일", "사장님", "월급", "언제",
    ],
}

# 온디바이스 에이전트 2단계용 — 증거 관련 키워드 (카테고리 무관하게 "증거일 가능성 있는" 단어)
EVIDENCE_KEYWORDS: list[str] = [
    # 급여
    "급여", "임금", "월급", "시급", "수당", "기본급", "실수령",
    "지급", "공제", "세전", "세후", "명세",
    # 계약
    "계약", "근로", "고용", "갑", "을", "서명", "날인",
    # 입금
    "입금", "출금", "이체", "잔액", "거래",
    # 근무
    "출근", "퇴근", "근무", "교대", "연장",
    # 분쟁
    "체불", "미지급", "노동", "신고",
]

# 카테고리가 서로 충돌하는지 판단할 때 쓰는 "강한 신호" 단어
# (이 단어가 보이면 거의 확실히 그 카테고리)
STRONG_SIGNALS: dict[str, list[str]] = {
    "contract": ["근로계약", "계약서", "연봉계약"],
    "statement": ["급여명세", "임금명세", "지급총액", "공제총액"],
    "payment": ["거래내역", "입출금", "잔액"],
    "schedule": ["근무표", "출퇴근기록"],
}


def keyword_score(category: str, text: str) -> int:
    """주어진 카테고리의 키워드가 text에 몇 개 등장하는지 센다."""
    if not text or category not in CATEGORY_KEYWORDS:
        return 0
    lowered = text.lower()
    return sum(1 for kw in CATEGORY_KEYWORDS[category] if kw.lower() in lowered)


def best_keyword_category(text: str) -> tuple[str | None, int]:
    """text에서 키워드 점수가 가장 높은 카테고리와 점수를 반환.
    매칭이 하나도 없으면 (None, 0)."""
    if not text:
        return None, 0
    scores = {cat: keyword_score(cat, text) for cat in CATEGORY_KEYWORDS}
    best = max(scores, key=lambda c: scores[c])
    return (best, scores[best]) if scores[best] > 0 else (None, 0)


def verify_category(category: str, text: str) -> dict:
    """classify가 낸 category를 OCR 텍스트 키워드로 검증.

    반환:
      {
        "agree": bool,          # 형태 분류와 내용 키워드가 일치하는가
        "category_score": int,  # 해당 카테고리 키워드 매칭 수
        "best_category": str|None,  # 텍스트상 가장 강한 카테고리
        "best_score": int,
        "conflict": bool,       # 다른 카테고리의 강한 신호가 더 우세한가
        "note": str,
      }
    """
    cat_score = keyword_score(category, text)
    best_cat, best_score = best_keyword_category(text)

    # 텍스트가 비었으면(이미지 OCR 실패/대화캡처 등) 검증 보류
    if not text or not text.strip():
        return {
            "agree": False, "category_score": 0, "best_category": None,
            "best_score": 0, "conflict": False,
            "note": "OCR 텍스트가 없어 내용 대조를 못했어요(이미지 분류만 사용).",
        }

    # 충돌: 다른 카테고리가 강한 신호로 더 우세할 때
    conflict = False
    note = ""
    if best_cat and best_cat != category and best_score > cat_score:
        # best_cat 쪽에 강한 신호가 있으면 충돌로 본다
        strong = STRONG_SIGNALS.get(best_cat, [])
        if any(s.lower() in text.lower() for s in strong):
            conflict = True
            note = f"형태는 '{category}'인데 내용은 '{best_cat}' 단어가 더 강해요. 확인이 필요해요."

    agree = cat_score > 0 and not conflict
    if agree and not note:
        note = f"내용에서 '{category}' 관련 단어 {cat_score}개 확인."
    elif not agree and not conflict and not note:
        note = f"'{category}' 관련 단어가 내용에서 안 보여요. 확인이 필요해요."

    return {
        "agree": agree,
        "category_score": cat_score,
        "best_category": best_cat,
        "best_score": best_score,
        "conflict": conflict,
        "note": note,
    }
