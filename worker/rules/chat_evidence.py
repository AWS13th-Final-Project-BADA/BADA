"""카톡 캡처 증거력 자동 평가 — 규칙 기반(생성형 X).

OCR이 뽑은 발화·발화자·날짜·금액으로 "증거성 높은/약한 캡처"를 구분하고
체크리스트 + 신뢰점수 + 누락경고를 만든다. (docs/ocr-roadmap.md 5장)
법적 판단이 아니라 '상담 준비 시 어떤 자료를 더 보강하면 좋은지' 안내용.
"""
from __future__ import annotations

_KEY_KINDS = {"wage_promise", "underpayment_admit"}        # 지급약속 / 체불인정
_REL_KINDS = {"wage_promise", "underpayment_admit", "work_order"}  # 사건 관련
_UNKNOWN_SPEAKER = {"", "?", "불명", "불명확", "미상", "unknown"}


def assess_chat(entities: dict) -> dict:
    """entities: OCR 추출 결과. 반환: {checklist, score, max_score, level, warnings, key_statements}."""
    utt = entities.get("utterances") or []
    dates = entities.get("dates") or []
    amounts = entities.get("amounts") or []

    speakers = {(u.get("speaker") or "").strip() for u in utt}
    speakers = {s for s in speakers if s.lower() not in _UNKNOWN_SPEAKER}
    kinds = {u.get("kind") for u in utt}

    checklist = {
        "상대 식별 가능": bool(speakers),
        "날짜 표시": bool(dates),
        "앞뒤 맥락(3줄 이상)": len(utt) >= 3,
        "지급약속/체불인정 문장": bool(kinds & _KEY_KINDS),
        "금액 언급": bool(amounts),
    }
    score = sum(1 for v in checklist.values() if v)
    level = "high" if score >= 4 else ("medium" if score >= 2 else "low")

    warnings = []
    if not checklist["상대 식별 가능"]:
        warnings.append("상대 식별 불가 — 발화자(사업주/근로자)가 보이는 캡처가 필요합니다.")
    if not checklist["날짜 표시"]:
        warnings.append("날짜/시각이 안 보입니다 — 날짜가 보이는 화면을 함께 캡처하세요.")
    if not checklist["앞뒤 맥락(3줄 이상)"]:
        warnings.append("중간 대화 누락 가능 — 핵심 문장 앞뒤 3~5줄을 포함해 다시 캡처하세요.")
    if not checklist["지급약속/체불인정 문장"]:
        warnings.append("지급약속·체불인정 문장이 보이지 않습니다.")

    key_statements = [
        {"speaker": u.get("speaker"), "text": u.get("text"), "kind": u.get("kind")}
        for u in utt if u.get("kind") in _REL_KINDS
    ]

    return {
        "checklist": checklist,
        "score": score,
        "max_score": len(checklist),
        "level": level,
        "warnings": warnings,
        "key_statements": key_statements,
    }
